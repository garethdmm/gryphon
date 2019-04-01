# -*- coding: utf-8 -*-
import os
import requests
import random
from delorean import epoch, Delorean
from collections import OrderedDict
from datetime import datetime, timedelta
from gryphon.lib.money import Money
from gryphon.lib.cache import cache_me

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class BitcoinWisdom(object):
    def __init__(self, exchange='bitstamp'):
        self.base_url = 'https://s5.bitcoinwisdom.com/%s'
        self.exchange = exchange.lower()
        self.symbol = 'btcusd'
        if self.exchange == 'cavirtex':
            self.symbol = 'btccad'
        elif self.exchange == 'vaultofsatoshi':
            self.exchange = 'vos'
            self.symbol = 'btccad'
        elif self.exchange == 'kraken':
            self.symbol = 'btceur'
        
        self.steps ={
                '1m': 60,'3m': 180,'5m': 300,'15m': 900,'30m':1800,
                '1h':3600,'2h':7200,'4h':14400,'6h':21600,'12h':43200,
                '1d':86400,'3d':259200,'1w':604800
            }

    # currently caching for a day, maybe longer in the future
    @cache_me(time=86400, ignore_self=True)
    def req_with_cache(self, url):        
        return self.req(url)

    def req(self, url):
        url = url + ('&nonce=%s' % 5408178796808)
        try:
            return requests.get(url).json()
        except ValueError:
            return None

    def create_url(self, step):
        step_seconds = self.steps[step]
        url = 'period?step=%s&symbol=%s%s' % (step_seconds, self.exchange, self.symbol)
        url = self.base_url % url
        return url
    
    def determine_step(self, start_date, end_date):
        if (end_date - start_date) >= timedelta(days=1):
            step = '1d'
        elif (end_date - start_date) >= timedelta(hours=1):
            step='1h'
        else:
            step = '1m'
        return step
    
   
    def period(self, start_date, end_date, step='1d', sid=''):
        if self.should_cache_this_result(start_date, end_date):
            points = self.req_with_cache(self.create_url(step))
        else:
            points = self.req(self.create_url(step))

        if not points:
            return OrderedDict()
        point_hash = OrderedDict()
        for p in points:
            point_hash[epoch(p[0]).naive] = Money(str(p[7]), 'BTC')
        return point_hash
    

    def volume_in_period(self, start_date, end_date):
        start_date = Delorean(start_date, 'UTC').datetime
        end_date = Delorean(end_date, 'UTC').datetime
        total_volume = Money(0, 'BTC')

        periods = self.period(
            start_date,
            end_date,
            step=self.determine_step(start_date, end_date),
        )

        for k,v in periods.iteritems():
            t=Delorean(k, 'UTC').datetime
            vol=v
            if t >= start_date and t < end_date:
                total_volume += vol

        return total_volume


    def should_cache_this_result(self, start_date, end_date):
        five_hours_ago = Delorean(datetime.now() - timedelta(hours=5), 'UTC').datetime

        return end_date < five_hours_ago


