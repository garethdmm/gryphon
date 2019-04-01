"""
This class re-implements the common methods of the ExchangeAPIWrapper class in a way
that also records the activity in a mysql database.

It also provides some other functions that can be useful for tracking activity on the
exchange account.

Currently this does not support the exchange wrapper's use of request-futures, but it
shouldn't be too hard to do so. You simply do most of the db work in the resp function.

To the strategies, this should appear to be an ExchangeAPIWrapper, but under the hood
it makes sure that our database does not get out of sync with our our account with the
exchange.
"""

import pyximport; pyximport.install()

from sets import Set

from cdecimal import Decimal, ROUND_UP, ROUND_DOWN
from delorean import Delorean
from sqlalchemy.orm import joinedload

from gryphon.execution.lib import auditing
from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.exchange.retry import exchange_retry
from gryphon.lib.models.datum import Datum
from gryphon.lib.models.event import EventRecorder
from gryphon.lib.models.order import Order
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.money import Money
from gryphon.lib.session import commit_mysql_session
from gryphon.lib.util.profile import tick_profile


class ExchangeCoordinator(object):
    def __init__(self, exchange_wrapper, db, harness=None):
        self.db = db
        self.exchange_wrapper = exchange_wrapper
        self.harness = harness
        self.is_tradable = False

        # Coordinators can only be used for trading if they are connected to an
        # initialized ledger in the data store, but they can be used for public
        # exchange API functions like get_orderbook().
        try:
            self.exchange_account = self.exchange_wrapper.exchange_account_db_object(db)
            self.is_tradable = True
        except AssertionError:
            self.exchange_account = None

        # TBD whether this has any purpose here. Execute/no-execute should be handled
        # in harness.pyx I think, but it still might be useful to have a dry-run mode
        # in ExchangeCoordinator for tests maybe.
        # self.execute = False

        # This represents whether this exchange has had any trading activity on it
        # since the last audit. If not, there's no reason to run consolidate_ledger()
        # or audit() for this exchange. Potentially, we could make this even less
        # strict, setting this to False whenever there are no orders left on the books.
        self.is_active = False
  
        """
        This actually means that we won't audit in no-execute mode.
        We do want audits to take place even if nothing has happened... hmm...
        """

    def consolidate_ledger(self):
        """
        To subsume harness::run_accounting
        """
        open_orders = self.get_open_orders()
        eaten_order_ids, current_orders = self._get_current_orders(open_orders)
        self._run_accounting(eaten_order_ids, current_orders)

        return current_orders

    @tick_profile
    def _get_current_orders(self, exchange_open_orders):
        db_open_orders = self._get_db_open_orders()
        db_open_order_ids = Set([o.exchange_order_id for o in db_open_orders])

        exchange_open_order_ids = Set([o['id'] for o in exchange_open_orders])
        eaten_order_ids = db_open_order_ids - exchange_open_order_ids
        current_order_ids = db_open_order_ids & exchange_open_order_ids

        unexpected_order_ids = exchange_open_order_ids - db_open_order_ids

        if unexpected_order_ids:
            self.handle_unexpected_orders(unexpected_order_ids)

        current_orders = []

        for order in exchange_open_orders:
            if order['id'] in current_order_ids:
                current_orders.append(order)

        return eaten_order_ids, current_orders

    def _run_accounting(self, eaten_order_ids, current_orders):
        """
        This function runs before each tick and guarantees that our ledger is consistent
        with the exchange's state as we enter the tick body.

        eaten_order_ids are the exchange order ids that have disappeared form the open
            state on the exchange since the last tick.

        current_orders are the entries from the response to exchange.open_orders that
            aren't in unexpected_order_ids.

        This function does something very similar in each case.
            - get the exchange details for the order
            - get the db order
            - run was_eaten/was_partially_eaten, save the order, and update
              the exchange_account position

        The only difference is for current orders we only do the last step if their
        volume_remaining has changed.
        """

        if eaten_order_ids:
            eaten_order_details = self.get_multi_order_details(eaten_order_ids)
            order_ids = eaten_order_details.keys()
            orders = self._get_orders_by_order_ids(order_ids)

            for order in orders:
                order_data = eaten_order_details[order.exchange_order_id]

                position_change, position_change_no_fees = order.was_eaten(order_data)
                self._save_order(order)
                self.update_position(position_change, position_change_no_fees)

                self.harness.log_trade(
                    position_change_no_fees[self.exchange_wrapper.currency],
                    position_change_no_fees[self.exchange_wrapper.volume_currency],
                )

        for current_order_from_exchange in current_orders:
            current_order_from_db = self._get_orders_by_order_ids(
                [current_order_from_exchange['id']],
            )[0]

            # Partially filled.
            if (current_order_from_exchange['volume_remaining'] 
                    < current_order_from_db.volume_remaining):

                details_result = self.get_multi_order_details(
                    [current_order_from_exchange['id']],
                )

                current_order_details = details_result[current_order_from_exchange['id']]

                position_change, position_change_no_fees = current_order_from_db.was_partially_eaten(current_order_details)

                self._save_order(current_order_from_db)
                self.update_position(position_change, position_change_no_fees)

                self.harness.log_trade(
                    position_change_no_fees[self.exchange_wrapper.currency],
                    position_change_no_fees[self.exchange_wrapper.volume_currency],
                )

    def handle_unexpected_orders(self, unexpected_order_ids):
        """
        Any orders that we find are open on the exchange account, but according to
        our ledger shouldn't be, are handled in this function. It considers three cases,
        documented in comments.
        """
        db_unexpected_orders = self._get_orders_by_order_ids(unexpected_order_ids)
        db_unexpected_order_ids = [o.exchange_order_id for o in db_unexpected_orders]

        # Case one, there are open orders on the exchange that are nowhere to be found
        # in our database.
        if set(db_unexpected_order_ids) != set(unexpected_order_ids):
            raise auditing.AuditException(
                'Unexpected Orders (not in db): %s' % unexpected_order_ids,
            )

        # Case two, there are orders open on the exchange that are neither open nor
        # cancelled in our database.
        real_unexpected_orders = [
            o for o in db_unexpected_orders if o.status != 'CANCELLED'
        ]

        if real_unexpected_orders:
            raise auditing.AuditException(
                'Unexpected Orders (shouldn\'t be in open state on exchange): %s' % [
                o.exchange_order_id for o in real_unexpected_orders
            ])

        # Case three, orders that are open on the exchange but are cancelled in our
        # database. This is probably just a past request failure, so we just try to
        # re-cancel them and let the next iteration of sync_ledger re-examine them.
        should_have_been_cancelled_orders = [
            o for o in db_unexpected_orders if o.status == 'CANCELLED'
        ]

        for o in should_have_been_cancelled_orders:
            #self.harness.log(
            #    '#%s should have been cancelled. Trying again.', o.exchange_order_id,
            #)

            o.status = 'OPEN'

            self.db.add(o)

            self.cancel_order(o.exchange_order_id)

    def _get_orders_by_order_ids(self, order_ids):
        return self.db.query(Order)\
            .filter_by(_exchange_name=self.exchange_wrapper.name)\
            .filter(Order.exchange_order_id.in_(order_ids))\
            .all()

    def _get_db_open_orders(self):
        return self.db.query(Order)\
            .filter_by(_exchange_name=self.exchange_wrapper.name)\
            .filter_by(status=Order.OPEN)\
            .options(joinedload('datums'))\
            .all()

    def update_position(self, position_change, position_change_no_fees):
        """
        Formerly harness:update_position.
        """ 
        for currency_code, position in position_change.iteritems():
            self.exchange_account.position[currency_code] += position
            self.exchange_account.balance[currency_code] += position

        self.db.add(self.exchange_account)
        commit_mysql_session(self.db)

    ## Trading interface functions. ##

    def limit_order(self, mode, volume, price, extra_data=[]):
        return self.place_order(
            mode,
            volume,
            price,
            order_types.LIMIT_ORDER,
            extra_data,
        )

    def market_order(self, mode, volume, price, extra_data=[]):
        return self.place_order(
            mode,
            volume,
            price,
            order_types.MARKET_ORDER,
            extra_data,
        )

    def place_order(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER, extra_data=[]):
        # TODO: this constant should be moved into the exchange wrapper library.
        # TODO: Give some messaging here why the order isn't being placed.
        if volume <= self.exchange_wrapper.min_order_size:
            return

        actor = Order.NULL_ACTOR

        if self.harness is not None:
            actor =  self.harness.strategy.actor

        # Some exchanges only let you place orders to price precision less than a cent.
        # In this case we round the order price in the most conservative direction.
        if self.exchange_wrapper.price_decimal_precision != None:
            if mode == Consts.BID:
                price = price.round_to_decimal_places(
                    self.exchange_wrapper.price_decimal_precision,
                    ROUND_DOWN,
                )
            elif mode == Consts.ASK:
                price = price.round_to_decimal_places(
                    self.exchange_wrapper.price_decimal_precision,
                    ROUND_UP,
                )
            else:
                raise Exception('Order type must be one of Bid or Ask!')

        # Some exchanges also have volume precision that is less than the native
        # precision of that currency.
        if self.exchange_wrapper.volume_decimal_precision != None:
            volume = volume.round_to_decimal_places(
                self.exchange_wrapper.volume_decimal_precision,
                ROUND_DOWN,
            )

        self.harness.log(
            'Placing order: %s for %s %.4f at %s',
            (mode, volume.currency, volume.round_to_decimal_places(4), price),
            color='red',
        )

        if self.harness.execute:
            self.is_active = True

            new_order = self._place_order_on_exchange(mode, volume, price, order_type)

            order = Order(
                actor,
                mode,
                volume,
                price,
                self.exchange_wrapper,
                new_order['order_id'],
            )

            # TODO: Turn the FV column into a datum that market making strategies add.
            order.fundamental_value = Money('1', 'USD')

            order.exchange_rate = Money(
                '1',
                self.exchange_wrapper.currency,
            ).to('USD').amount
  
            if extra_data:
                order.datums = self._create_datums_from_extra_data(extra_data)

            self._save_order(order)

            return new_order
        else:  # no-execute.
            self.harness.log('Not placing order because execute=False')

    def _create_datums_from_extra_data(self, extra_data):
        """
        Accepts a dictionary of key-value pairs, where the keys are strings and the
        values are either strings or Decimals, and returns a list of Datum objects with
        equivalent data.
        """
        datums = []

        for datum_type, value in extra_data.items():
            if type(value) is str:
                datums.append(Datum(datum_type, string_value=value))
            elif type(value) is Decimal:
                datums.append(Datum(datum_type, numeric_value=value))
            elif type(value) is Money:
                datums.append(Datum(
                    datum_type,
                    numeric_value=value.amount,
                    string_value=value.currency,
                ))
            else:
                raise Exception(
                    'extra_data only supports str or cdecimal.Decimal types',
                )

        return datums

    @exchange_retry()
    def _place_order_on_exchange(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        new_order = self.exchange_wrapper.place_order(mode, volume, price, order_type)
        return new_order

    def _save_order(self, new_order):
        self.db.add(new_order)
        commit_mysql_session(self.db)

    @tick_profile
    @exchange_retry()
    def get_open_orders(self):
        return self.exchange_wrapper.get_open_orders()

    @exchange_retry()
    def cancel_order(self, order_id):
        try:
            self.exchange_wrapper.cancel_order(order_id)
        except exceptions.CancelOrderNotFoundError:
            # Don't place a new order if the order to cancel got eaten.
            pass

    def cancel_all_open_orders(self):
        # Won't this happen anyway with the getattr hack?
        self.exchange_wrapper.cancel_all_open_orders()

    @tick_profile
    @exchange_retry()
    def get_orderbook(self, open_orders=None):
        orderbook = self.exchange_wrapper.get_orderbook()

        if open_orders is not None:
            orderbook = self.exchange_wrapper.remove_orders_from_orderbook(
                orderbook,
                open_orders,
            )

        return orderbook

    @exchange_retry()
    def get_multi_order_details(self, order_ids):
        return self.exchange_wrapper.get_multi_order_details(order_ids)

    def __getattr__(self, name, *args):
        """
        Right now this class is a weird compromise between composition and inheritance
        with the ExchangeAPIWrapper class. In some senses this class 'has' an api
        wrapper, and in other senses it 'extends' the APIWrapper interface. An
        inheritance solution would have a ton of helper functions in this class that
        just dispatch to self.exchange_wrapper, which seems silly. On the other hand,
        we really do want all the methods on self.exchange_wrapper to be callable
        through this class. This function is a hack to ignore this conundrum for a
        little while, but likely comes with it's own dangers.

        It should be noted that the current method breaks the usage of the req/resp-
        style methods, as those will go straight to the exchange wrapper, but we can
        fix that later.
        """
        # Even better than this check would be `if name in ExchangeTradingInterface`
        if name in dir(self.exchange_wrapper):
            return self.exchange_wrapper.__getattribute__(name, *args)
        else:
            raise AttributeError(
                '\'%s\' object has no attribute \'%s\'' % (
                self.__class__.__name__,
                name,
            ))

    # Audits. #
    def audit(self, audit_types):
        self.exchange_wrapper.pre_audit(exchange_data=self.exchange_account)
        volume_tolerance = self.exchange_wrapper.volume_balance_tolerance
        fiat_tolerance = self.exchange_wrapper.fiat_balance_tolerance

        event_data = {}

        if auditing.ORDER_AUDIT in audit_types:
            order_audit_data = self.order_audit()

            if order_audit_data:
                event_data['order_data'] = order_audit_data

        balance_audit_data = None

        if auditing.VOLUME_BALANCE_AUDIT in audit_types:
            balance_audit_data = self.volume_balance_audit(volume_tolerance)

            if balance_audit_data:
                event_data['balance_data'] = balance_audit_data

        if auditing.FIAT_BALANCE_AUDIT in audit_types:
            # This returns the exact same balance_audit_data as
            # volume_balance_audit() so we don't need to record it here. We can also
            # skip a second balance() call to the exchange by passing in the result
            # of volume_balance_audit() if we've already called that.
            self.fiat_balance_audit(fiat_tolerance, exchange_balance=balance_audit_data)

        if auditing.POSITION_CACHE_AUDIT in audit_types:
            auditing.position_cache_audit(self.db, self.exchange_account)

        if auditing.LEDGER_AUDIT in audit_types:
            auditing.ledger_audit(self.exchange_account)

        EventRecorder().record(Consts.AUDIT, self.name, event_data)

        self.is_active = False

        self.harness.log('Audits Passed', color='green')

    @exchange_retry()
    def volume_balance_audit(self, tolerance, exchange_balance=None):
        self.harness.log(
            'volume_balance_audit(tolerance=%s)' % tolerance,
            log_level='debug',
        )

        return auditing.volume_balance_audit(
            self.exchange_wrapper,
            self.exchange_account,
            tolerance=tolerance,
            execute=self.harness.execute,
            exchange_balance=exchange_balance,
        )

    @exchange_retry()
    def fiat_balance_audit(self, tolerance, exchange_balance=None):
        self.harness.log(
            'fiat_balance_audit(tolerance=%s)' % tolerance,
            log_level='debug',
        )

        return auditing.fiat_balance_audit(
            self.exchange_wrapper,
            self.exchange_account,
            tolerance=tolerance,
            execute=self.harness.execute,
            exchange_balance=exchange_balance,
        )

    @exchange_retry()
    def order_audit(self):
        self.harness.log('order_audit()', log_level='debug')

        try:
            order_audit_data = auditing.order_audit(self.db, self.exchange_wrapper)
        except auditing.OrderAuditException as e:
            # These are all the orders which failed the order audit.
            failed_order_ids = [d[0] for d in e.failed_order_data]

            # We give the exchange a 2nd chance, hoping that things have settled down
            # and we will get the correct accounting this time. If we try to reopen an
            # order that probably shouldn't be, this will cause a failure and kill the
            # bot.
            self.reopen_orders(e.exchange, failed_order_ids)

            # There aren't any open orders because we're in an audit.
            eaten_order_ids, current_orders = self._get_current_orders([])  
            self._run_accounting(eaten_order_ids, current_orders)

            # Now we retry the original audit. If it fails again this will cause a
            # hard failure and kill the bot.
            order_audit_data = auditing.order_audit(self.db, self.exchange_wrapper)

        return order_audit_data

    def reopen_orders(self, exchange, exchange_order_ids):
        for exchange_order_id in exchange_order_ids:
            self.log(
                'Order Volume Mismatch on %s! Attempting to fix.',
                (exchange_order_id),
                'red',
            )

            order = self.db.query(Order)\
                .filter(Order._exchange_name == exchange.name)\
                .filter(Order.exchange_order_id == exchange_order_id)\
                .one()

            if (Delorean(order.time_created, 'UTC').datetime <
                    Delorean().last_hour(1).datetime):
                raise Exception(
                    'Trying to re-open an order that\'s more than an hour old!'
                )

            order.status = Order.OPEN

