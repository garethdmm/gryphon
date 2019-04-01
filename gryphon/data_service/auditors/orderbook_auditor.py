from collections import defaultdict
from datetime import timedelta
import json

from delorean import Delorean
from sqlalchemy import and_
import treq
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.python.filepath import FilePath

from gryphon.data_service.auditors.auditor import Auditor
import gryphon.data_service.util as util
from gryphon.lib.dict_differ import DictDiffer
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.exchange.base import Exchange
from gryphon.lib.metrics import midpoint
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook
from gryphon.lib.money import Money

metadata = EmeraldHavocBase.metadata
orderbook_table = metadata.tables['orderbook']

# This determines how deep we audit the orderbook, necessary for performance reasons.
ORDERBOOK_PRICE_LIMIT = 10


class OrderbookAuditor(Auditor):
    def __init__(self):
        self.unsuccessful_audit_threshold = 4
        self.incomplete_audit_threshold = 60
        self.acceptable_fund_value_threshold = 0.0025
        self.acceptable_changes_threshold = 10
        self.audit_time = 10

    @defer.inlineCallbacks
    def start(self):
        self.setup_mysql()
        self.orderbook_timestamp = Delorean().datetime
        self.unsuccessful_audits = 0
        self.incomplete_audits = 0
        self.touch_path = 'monit/heartbeat/%s_orderbook.txt' % self.exchange_name.lower()
        self.looping_call = LoopingCall(self.pre_audit)
        self.looping_call.start(self.audit_time)
        self.redis = yield util.setup_redis()
        self.should_continue_key = '%s_orderbook_should_continue' % self.exchange_name.lower()
        self.redis.set(self.should_continue_key, 1)

    @defer.inlineCallbacks
    def pre_audit(self):
        if self.should_hard_fail():
            self.hard_fail()
            return

        try:
            # Coinbase requires a user agent
            headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0'}
            response = yield treq.get(self.orderbook_url, headers=headers)
            new_orderbook = yield treq.json_content(response)
        except Exception as e:
            log.msg('%s Orderbook Auditor: %s' % (self.exchange_name, str(e)))

            self.incomplete_audits += 1

            log.msg(
                '%s Incomplete Audits: %s' % (
                self.exchange_name,
                self.incomplete_audits,
            ))

            return

        new_orderbook_timestamp = self.get_timestamp(new_orderbook)

        if new_orderbook_timestamp <= self.orderbook_timestamp:
            # We already audited this orderbook.
            return

        self.orderbook_timestamp = new_orderbook_timestamp

        # Found orderbook. Auditing it 10s from now to make sure we have websocket
        # orderbooks in the -5s +5s db window we look up.
        reactor.callLater(10, self.audit, new_orderbook, new_orderbook_timestamp)

    @defer.inlineCallbacks
    def audit(self, orderbook, orderbook_timestamp):
        audit_successful = yield self.audit_orderbook(orderbook, orderbook_timestamp)

        if audit_successful == 'SOFT':
            self.unsuccessful_audits += 1

            if self.should_hard_fail():
                self.hard_fail()
            else:
                log.msg(
                    '%s Orderbook Audit Soft Failed: %s' % (
                    self.exchange_name,
                    self.unsuccessful_audits,
                ))
        elif audit_successful == 'HARD':
            self.hard_fail()
        else:
            FilePath(self.touch_path).touch()
            self.unsuccessful_audits = 0
            self.incomplete_audits = 0

            log.msg(
                '%s Orderbook Audit Passed on Timestamp:%s' % (
                self.exchange_name,
                orderbook_timestamp,
            ))

    def should_hard_fail(self):
        too_many_unsuccessful_audits = (
            self.unsuccessful_audits > self.unsuccessful_audit_threshold
        )

        too_many_incomplete_audits = (
            self.incomplete_audits > self.incomplete_audit_threshold
        )

        return too_many_unsuccessful_audits or too_many_incomplete_audits

    @defer.inlineCallbacks
    def hard_fail(self):
        log.err('%s Orderbook Auditor Declaring a Hard Failure' % self.exchange_name)

        yield self.redis.set(self.should_continue_key, 0)
        self.looping_call.stop()

    @defer.inlineCallbacks
    def audit_orderbook(self, orderbook, orderbook_timestamp):
        orderbook_timestamp_early = orderbook_timestamp - timedelta(seconds=5)
        orderbook_timestamp_late = orderbook_timestamp + timedelta(seconds=5)

        result = yield self.engine.execute(
            orderbook_table.select(orderbook_table).where(
                and_(
                    orderbook_table.c.exchange == self.exchange_name,
                    orderbook_table.c.timestamp.between(
                        orderbook_timestamp_early,
                        orderbook_timestamp_late))))

        our_orderbooks = yield result.fetchall()

        # Non Blocking ^^^
        # Potentially Blocking vvv

        start_time = Delorean().epoch
        audit_successful = 'SOFT'
        change_dict = {}
        fundamental_values = {}

        exchange_object = exchange_factory.make_exchange_from_key(self.exchange_name)

        price_limit = Money(ORDERBOOK_PRICE_LIMIT, exchange_object.currency)

        http_orderbook = exchange_object.parse_orderbook(
            orderbook,
            price_limit=price_limit,
        )

        http_fundamental_value = self.fundamental_value(http_orderbook)
        indexed_http_ob = self.index_orderbook(http_orderbook)

        for our_ob in our_orderbooks:
            raw_db_orderbook = {
                'bids': json.loads(our_ob.bids),
                'asks': json.loads(our_ob.asks),
            }

            db_orderbook = exchange_object.parse_orderbook(
                raw_db_orderbook,
                price_limit=price_limit,
                cached_orders=True,
            )

            # Check for soft falilures
            db_fundamental_value = self.fundamental_value(db_orderbook)

            fund_value_closeness = (
                abs(db_fundamental_value - http_fundamental_value)
                / http_fundamental_value
            )

            indexed_db_ob = self.index_orderbook(db_orderbook)

            ask_diffs = DictDiffer(indexed_db_ob['asks'], indexed_http_ob['asks'])
            bid_diffs = DictDiffer(indexed_db_ob['bids'], indexed_http_ob['bids'])

            changes = (
                list(ask_diffs.added()) +
                list(ask_diffs.removed()) +
                list(ask_diffs.changed()) +
                list(bid_diffs.added()) +
                list(bid_diffs.removed()) +
                list(bid_diffs.changed())
            )

            total_changes = len(changes)

            change_dict[total_changes] = changes
            fundamental_values[fund_value_closeness] = {
                'db_fundamental_value': db_fundamental_value,
                'http_fundamental_value': http_fundamental_value,
            }

            hard_failure_fund_value_closeness = 10

            if (total_changes < self.acceptable_changes_threshold and
                    fund_value_closeness < self.acceptable_fund_value_threshold):
                audit_successful = 'SUCCESSFUL'

            # Check for hard failures.
            if self.detect_orderbook_cross(db_orderbook):
                audit_successful = 'HARD'

                log.err('%s Auditor Detects Cross -  Bids:%s, Asks:%s' % (
                    self.exchange_name,
                    db_orderbook['bids'][:3],
                    db_orderbook['asks'][:3]
                ))

                break

            if fund_value_closeness > hard_failure_fund_value_closeness:
                audit_successful = 'HARD'

                log.err('Funamental Value difference is more than %s% its:' % (
                    hard_failure_fund_value_closeness,
                    fund_value_closeness
                ))

                break

        if not audit_successful == 'SUCCESSFUL':
            log.msg('%s Orderbook Auditor Soft Failure Report:' % self.exchange_name)

            if not our_orderbooks:
                log.msg('No orderbooks to audit against')

            for key, value in fundamental_values.iteritems():
                log.msg(
                    '------ Fundamental Value Closeness:%.6f, DBfv:%s, HTTPfv:%s' % (
                    key,
                    value['db_fundamental_value'],
                    value['http_fundamental_value']
                ))

            for key, value in change_dict.iteritems():
                log.msg('------ Change Count: %s' % key)

        log.msg(
            'Time Elapsed Auditing %s Orderbook: %s' % (
            self.exchange_name,
            Delorean().epoch - start_time,
        ))

        defer.returnValue(audit_successful)

    def index_orderbook(self, orderbook):
        """Returns bid and ask dictionary of price => volume."""

        indexed_orderbook = {}
        indexed_orderbook['bids'] = self.index_orders(orderbook['bids'])
        indexed_orderbook['asks'] = self.index_orders(orderbook['asks'])

        return indexed_orderbook

    def index_orders(self, orders):
        """Returns a dictionary of price => volume."""

        orders_dict = defaultdict(int)

        for order in orders:
            orders_dict[order.price.amount] += order.volume.amount

        return orders_dict

    def fundamental_value(self, orderbook):
        depth = Money('20', 'BTC')

        try:
            fundamental_value = midpoint.get_midpoint_from_orderbook(orderbook, depth)
        except:
            # Some very illiquid exchanges don't always have 20 BTC of depth.
            depth = Money('1', 'BTC')

            fundamental_value = midpoint.get_midpoint_from_orderbook(orderbook, depth)

        return fundamental_value

    def detect_orderbook_cross(self, orderbook):
        if orderbook['asks'] and orderbook['bids']:
            if orderbook['asks'][0].price <= orderbook['bids'][0].price:
                return True

        return False
