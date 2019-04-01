# -*- coding: utf-8 -*-
import json

import termcolor as tc
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.python import log

import gryphon.data_service.consts as consts
from gryphon.data_service.pollers.request_poller import RequestPoller
import gryphon.data_service.util as util


class TradesPoller(RequestPoller):
    @property
    def trade_id_key(self):
        return '%s_most_recent_trade_id' % self.exchange_name.lower()

    @property
    def heartbeat_key(self):
        return '%s_trades_heartbeat' % self.exchange_name.lower()

    @defer.inlineCallbacks
    def start(self):
        self.redis = yield util.setup_redis()

        binding_key = '%s.trades.tinker' % self.exchange_name.lower()
        self.producer = yield util.setup_producer(consts.TRADES_QUEUE, binding_key)

        raw_most_recent_trade_id = yield self.redis.get(self.trade_id_key)

        if raw_most_recent_trade_id:
            self.most_recent_trade_id = int(raw_most_recent_trade_id)
        else:
            self.most_recent_trade_id = 0

        # We are not using RequestPoller's start() function because we want to set
        # now=False. This is a bit of a hack to give the producer time to get set up
        # before we start publishing messages.
        self.looping_call = LoopingCall(self.get_request)
        self.looping_call.start(self.poll_time, now=False)

    @defer.inlineCallbacks
    def parse_response(self, resp_obj):
        trades = self.parse_trades(resp_obj)

        # oldest trade is the first one in the list
        trades = sorted(trades, key=lambda k: k['trade_id'])

        for trade in trades:
            if trade['trade_id'] > self.most_recent_trade_id:
                trade['price_currency'] = trade['price'].currency
                trade['price'] = unicode(trade['price'].amount)
                trade['volume_currency'] = trade['volume'].currency
                trade['volume'] = unicode(trade['volume'].amount)
                trade['timestamp'] = int(trade['timestamp'])
                trade_string = json.dumps(trade, ensure_ascii=False)
                self.producer.publish_message(trade_string)
                self.most_recent_trade_id = trade['trade_id']

        if (trades[0]['trade_id'] > self.most_recent_trade_id
                and self.most_recent_trade_id > 0):
            log.msg(tc.colored('Trades Missed on %s' % self.exchange_name, 'red'))

        yield self.redis.set(self.trade_id_key, self.most_recent_trade_id)

    @defer.inlineCallbacks
    def parse_trades(self, trade_dict):
        pass
