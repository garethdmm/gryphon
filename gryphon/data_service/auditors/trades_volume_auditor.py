# -*- coding: utf-8 -*-
from datetime import timedelta

from delorean import Delorean
from sqlalchemy import and_
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from twisted.python import log

from gryphon.data_service.auditors.auditor import Auditor
import gryphon.data_service.util as util
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
from gryphon.lib.twistedbitcoinwisdom import TwistedBitcoinWisdom

metadata = EmeraldHavocBase.metadata
trades = metadata.tables['trade']


EXCHANGES = ['KRAKEN', 'BITSTAMP', 'BITFINEX', 'CAVIRTEX', 'VAULTOFSATOSHI']


class TradesVolumeAuditor(Auditor):
    def start(self):
        self.redis = yield util.setup_redis()
        self.setup_mysql()
        self.looping_call = LoopingCall(self.audit).start(30)

    @defer.inlineCallbacks
    def target_volume_in_trade_list(self, trade_list, target_volume):
        n = len(trade_list)
        found_match = False

        def offline_summation(lower_bound, upper_bound, trade_list, trades, target_volume):
            perm_sum = 0

            for k in range(lower_bound, upper_bound):
                perm_sum += trade_list[k][trades.c.volume]

            return perm_sum == target_volume

        if not n:
            defer.returnValue(target_volume == 0)
        elif target_volume == 0:
            # TODO Fix this.
            defer.returnValue(False)
        else:
            for i in range(n):
                for j in range(n - i, n + 1):
                    found_match = yield reactor.callLater(
                        0,
                        offline_summation,
                        j - (n - i),
                        j,
                        trade_list,
                        trades,
                        target_volume,
                    )

                    if found_match:
                        break

            defer.returnValue(found_match)

    @inlineCallbacks
    def audit(self, exchanges=EXCHANGES):
        now = Delorean().datetime
        outer_min = now
        outer_max = Delorean(now - timedelta(minutes=9)).datetime
        inner_max = Delorean(now - timedelta(minutes=6)).datetime
        inner_min = Delorean(now - timedelta(minutes=3)).datetime

        for exchange in exchanges:
            real_volume = yield TwistedBitcoinWisdom(exchange=exchange)\
                .volume_in_period(inner_max, inner_min)

            real_volume = real_volume.amount

            result = yield self.engine.execute(
                trades.select(trades)
                .where(and_(
                    trades.c.exchange.startswith(exchange),
                    trades.c.timestamp.between(outer_max, outer_min),
                ))
            )

            d_trades = yield result.fetchall()

            target_in_trades = yield self.target_volume_in_trade_list(
                d_trades,
                real_volume,
            )

            if not target_in_trades:
                log.err('Trade Volume Audit Failed : %s' % (exchange))
            else:
                log.msg('Trade Volume Audit Passed : %s' % (exchange))

