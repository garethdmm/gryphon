from delorean import Delorean
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.python.filepath import FilePath

from gryphon.data_service.auditors.auditor import Auditor
import gryphon.data_service.util as util


class HeartbeatAuditor(Auditor):
    @defer.inlineCallbacks
    def start(self):
        self.touch_path = 'monit/heartbeat/twisted.txt'
        self.redis = yield util.setup_redis()

        self.heartbeat_threshold = 120
        self.heartbeats = [
            'bitfinex_trades_heartbeat',
            'bitstamp_btc_usd_trades_heartbeat',
            'coinbase_btc_usd_trades_heartbeat',
            'itbit_trades_heartbeat',
            'kraken_trades_heartbeat',
            'kraken_usd_trades_heartbeat',
            'kraken_cad_trades_heartbeat',
            'okcoin_trades_heartbeat',
            #'coinbase_cad_trades_heartbeat',
            'gemini_trades_heartbeat',
            'quadriga_trades_heartbeat',

            'okcoin_orderbook_heartbeat',
            'bitstamp_btc_usd_orderbook_heartbeat',
            'kraken_orderbook_heartbeat',
            'kraken_usd_orderbook_heartbeat',
            'kraken_cad_orderbook_heartbeat',
            'itbit_orderbook_heartbeat',
            'coinbase_btc_usd_orderbook_heartbeat',
            #'coinbase_cad_orderbook_heartbeat',
            'bitfinex_orderbook_heartbeat',
            'quadriga_orderbook_heartbeat',
            'gemini_orderbook_heartbeat',

            'gemini_eth_btc_orderbook_heartbeat',
            'bitstamp_eth_btc_orderbook_heartbeat',
            'poloniex_eth_btc_orderbook_heartbeat',

            'gemini_eth_usd_orderbook_heartbeat',
            'bitstamp_eth_usd_orderbook_heartbeat',

            'bitstamp_eth_eur_orderbook_heartbeat',
            'bitstamp_bch_eur_orderbook_heartbeat',
            'bitstamp_bch_usd_orderbook_heartbeat',
            'bitstamp_bch_btc_orderbook_heartbeat',
            'bitstamp_btc_eur_orderbook_heartbeat',

            'open_exchange_rate_poller_heartbeat',
        ]

        self.looping_call = LoopingCall(self.audit)
        self.looping_call.start(30)

    @defer.inlineCallbacks
    def audit(self):
        successful_heartbeat_check = True
        now = Delorean().epoch

        for heartbeat_key in self.heartbeats:
            last_heartbeat = yield self.redis.get(heartbeat_key)
            last_heartbeat = float(last_heartbeat) if last_heartbeat else 0
            heartbeat_age = now - last_heartbeat

            if heartbeat_age > self.heartbeat_threshold:
                log.msg(
                    '[Heartbeat Auditor] Failure %s: %ds is older than %ds' % (
                    heartbeat_key,
                    heartbeat_age,
                    self.heartbeat_threshold,
                ))

                successful_heartbeat_check = False

        if successful_heartbeat_check:
            log.msg('[Heartbeat Auditor] Passed')
            FilePath(self.touch_path).touch()
        else:
            log.msg('[Heartbeat Auditor] Failed')
