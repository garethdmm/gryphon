# -*- coding: utf-8 -*-
import os
import requests
import random
from delorean import epoch, Delorean
from collections import OrderedDict
from datetime import datetime, timedelta
from gryphon.lib.money import Money
from gryphon.lib.bitcoinwisdom import BitcoinWisdom


class TwistedBitcoinWisdom(BitcoinWisdom):
    
    from twisted.internet import defer
    from twisted.python import log

    @defer.inlineCallbacks
    def volume_in_period(self, start_date, end_date):
        from twisted.internet import defer
        total_volume = Money(0, 'BTC')
        periods = yield self.period(step=self.determine_step(start_date, end_date))
        for k,v in periods.iteritems():
            t=Delorean(k, 'UTC').datetime
            vol=v
            if t >= start_date and t < end_date:
                total_volume += vol
        defer.returnValue(total_volume)
    
    @defer.inlineCallbacks
    def period(self, step='1d', sid=''): 
        from twisted.internet import defer
        points = yield self.req(self.create_url(step))
        if not points:
            defer.returnValue(OrderedDict())
        point_hash = OrderedDict()
        for p in points:
            point_hash[epoch(p[0]).naive] = Money(str(p[7]), 'BTC')
        defer.returnValue(point_hash)
    
    @defer.inlineCallbacks
    def req(self, url):
        import treq
        from twisted.internet import defer
        response = yield treq.get('%s&nonce=5408178796808' % url)
        json_response = yield treq.json_content(response)
        a = yield json_response
        defer.returnValue(a)
 
    
