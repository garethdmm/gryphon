# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
import json
import os
import uuid

from decimal import *

from gryphon.lib import gryphon_json_serialize
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money


class BasicOrder(object):
    
    #Uncompleted statuses
    OPEN = u'OPEN'
    FILLED = u'FILLED'
    CANCELLED = u'CANCELLED'
    REVERSED = u'REVERSED'

    #Order Types
    BID = Consts.BID
    ASK = Consts.ASK
  
    # Special Actors
    NULL_ACTOR = u'NULL'

    def __unicode__(self):
        return u'[ORDER:%s:%s:%s] Status:%s, Price:%s, Volume:%s BTC' % (
            self.order_type, self.exchange.name, self.currency, self.status, self.price, self.volume)
        
    def __repr__(self):
        return self.to_json()

    #override
    def to_json(self):
        raise NotImplementedError


    #override
    def set_trades(self, trades):
        raise NotImplementedError

    def was_eaten(self, order_details):
        old_position = self.position
        self.time_executed = datetime.utcnow()
        if order_details['btc_total'] <= 0:
            self.status = BasicOrder.CANCELLED
        else:
            self.status = BasicOrder.FILLED
            # TODO store the volume filled amount in order?
            self.time_executed = datetime.utcnow()
            self.set_trades(order_details['trades'])
        return self.position_change(old_position)

    # returns position change
    def was_partially_eaten(self, order_details):
        old_position = self.position
        self.set_trades(order_details['trades'])
        return self.position_change(old_position)

    @property
    def exchange(self):
        if hasattr(self, '_exchange'):
            return self._exchange
        elif self._exchange_name:
            self._exchange = make_exchange_from_key(self._exchange_name)
            return self._exchange
        else:
            return None
        
    @exchange.setter
    def exchange(self, value):
        self._exchange = value
        self._exchange_name = self._exchange.name
    
    
    @property
    def volume(self):
        return Money(self._volume, 'BTC')

    @volume.setter
    def volume(self, value):
        self._volume = value.amount
    
    @property
    def price(self):
        return Money(self._price, 'USD')

    @price.setter
    def price(self, value):
        self._price = value.amount

    #override
    @property
    def volume_filled(self):
        raise NotImplementedError

    @property
    def volume_remaining(self):
        return self.volume - self.volume_filled

    #override
    @property
    def position(self):
        raise NotImplementedError

    def position_change(self, old_position, include_fees=True):
        """
        Returns the difference between an old position and the current position.

        If you are excluding fees, make sure you have also excluded them
        when calculating old_position
        """
        return self.calc_position(include_fees) - old_position
