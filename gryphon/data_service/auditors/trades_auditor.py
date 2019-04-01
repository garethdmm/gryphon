# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import subprocess

from cdecimal import Decimal
from sqlalchemy import and_, func, select
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from twisted.python import log

from gryphon.data_service.auditors.auditor import Auditor
import gryphon.data_service.util as util
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
from gryphon.lib.models.emeraldhavoc.exchange_volume import ExchangeVolume
from gryphon.lib.models.emeraldhavoc.trade import Trade
from gryphon.lib.slacker import Slacker

metadata = EmeraldHavocBase.metadata
trades = metadata.tables['trade']
exchange_volumes = metadata.tables['exchange_volume']


class TradesAuditor(Auditor):
    def __init__(self, exchanges=[]):
        self.exchanges = exchanges

    def heartbeat(self, response=None):
        subprocess.call(["touch", "monit/heartbeat/trades_auditor_heartbeat.txt"])

    @defer.inlineCallbacks
    def start(self):
        self.redis = yield util.setup_redis()
        self.setup_mysql()
        self.heartbeat_key = 'trades_auditor_heartbeat'
        self.looping_call = LoopingCall(self.audit).start(1800)
        self.accuracy_bottom = Decimal('0.99')
        self.accuracy_top = Decimal('1.01')
        self.slacker = Slacker('#notifications', 'Auditor')

    @inlineCallbacks
    def audit(self):
        successes = []

        for exchange in self.exchanges:
            now = datetime.utcnow()
            twenty_four_hours_ago = now - timedelta(hours=24)
            ten_minutes_ago = now - timedelta(minutes=10)

            trades_sum_result = yield self.engine.execute(
                select([func.sum(trades.c.volume)])
                .where(and_(
                    trades.c.exchange.__eq__(exchange),
                    trades.c.timestamp.between(twenty_four_hours_ago, now),
                ))
            )

            trades_sum_result = yield trades_sum_result.fetchone()
            trades_volume = trades_sum_result[0] or 0

            exchange_volume_result = yield self.engine.execute(
                select([exchange_volumes.c.exchange_volume])
                .where(and_(
                    exchange_volumes.c.exchange.__eq__(exchange),
                    exchange_volumes.c.timestamp.between(ten_minutes_ago, now),
                ))
                .order_by(exchange_volumes.c.timestamp.desc())
            )

            exchange_volume_result = yield exchange_volume_result.fetchone()

            if exchange_volume_result:
                most_recent_exchange_volume = exchange_volume_result[0]

                accuracy = trades_volume / most_recent_exchange_volume
                log.msg('Trade Volume Accuracy on %s: %s' % (exchange, accuracy))

                if accuracy < self.accuracy_bottom or accuracy > self.accuracy_top:
                    successes.append(False)

                    self.slacker.notify(
                        '%s Trades Poller at %s accuracy. Outside %s-%s' % (
                        exchange,
                        accuracy,
                        self.accuracy_bottom,
                        self.accuracy_top,
                    ))
                else:
                    successes.append(True)

        # If all exchanges passed their audit then we heartbeat.
        if all(successes):
            self.heartbeat()
