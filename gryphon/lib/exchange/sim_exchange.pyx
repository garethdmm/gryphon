# -*- coding: utf-8 -*-
import time
import os
import datetime
import logging
import json
import math
import uuid
import copy
from gryphon.lib.money import Money
from gryphon.lib.exchange.base import Exchange
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.exchange import Balance

from cdecimal import *
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimExchange(Exchange):
    
    def __init__(self, data_source=None, debug=False, engine=None):
        self.name = u'SIM'
        self.friendly_name = u'Sim'
        self.currency = u'USD'
        self.fee = Decimal("0.0000")
        
        if not engine:
            raise("Please pass an Engine.")
        self.engine = engine
        self.order_ids_buffer = []
     
    def fill_order_book(self, num_ticks=500):
        for i in range(num_ticks):
            self.engine._tick(self)
       
    # override this because we take the orders out in the engine
    def remove_our_orders(self, order_book, open_orders):
        pass


    ###### Common Exchange Methods ######

    # modifies request_args
    def auth_request(self, req_method, url, request_args):
        return None

    def balance_req(self):
        account_balance = self.engine.balance()
        logger.info('account_balance %s ' % account_balance)
        usd_balance = account_balance['usd']
        btc_balance = account_balance['btc']
        logger.info(u'[Sim Exchange] Balance: %s BTC %s USD' % (btc_balance, usd_balance))
        balance = Balance()
        balance['BTC'] = btc_balance
        balance['USD'] = usd_balance
        return balance

    def balance_resp(self, req):
        return req
    
    def get_order_book_req(self, debug=False, verify=True):
        # get the iteration number
        orderbook = self.engine.order_book(self, without_user_orders=True, debug=debug)
        return orderbook
       
    def get_order_book_resp(self, req, volume_limit=None):
        return req

    def create_trade_req(self, mode, volume, price):
        order = None

        #print volume

        if mode == Consts.ASK:
            order = self.engine.ask(volume, price, self)
        elif mode == Consts.BID:
            order = self.engine.bid(volume, price, self)
        else:
            raise ValueError('mode must be Consts.ASK or Consts.BID')
  
        return {
            'success':True,
            'order_id':order.order_id
        }
        
        
    def create_trade_resp(self, req):
        return req
    
    
    def open_orders_req(self):
        open_orders = self.engine.open_orders()
        open_orders_dicts = []
        for o in open_orders:
            order_type = o.type
            open_orders_dicts.append({
                'mode':order_type,
                'id':o.order_id,
                'price':o.price,
                'volume_remaining':o.volume
            })
        return open_orders_dicts
        
    def open_orders_resp(self, req):
        return req

    def multi_order_status_req(self):
        return None
        
    def multi_order_status_resp(self, req, order_ids):
        status_dict = {}
        for order_id in order_ids:
            order = self.engine.order_status(order_id)
            status = ''
            if order.status == Order.OPEN:
                status = 'open'
            elif order.status == Order.PARTIALLY_FILLED:
                status = 'open'
            elif order.status == Order.CANCELLED:
                status = 'cancelled'
            elif order.status == Order.FILLED:
                status = 'filled'
            else:
                status = 'error'
            status_dict[order_id] = {'status': status}
        return status_dict
            
    def order_details_req(self, order_id):
        self.order_ids_buffer.append(order_id)
        return None
    
    def order_details_resp(self):
        order_id = self.order_ids_buffer.pop()
        order = self.engine.order_status(order_id)
        if not order:
            raise Exception('You asked for an order that does not exist.')
        
        trades_dicts = []
        trades = self.engine.get_trades(order_id)
        fiat_total = Money(0, 'USD')
        for trade in trades:
            fiat_trade = trade.price * trade.volume.amount 
            fiat_total += fiat_trade
            trades_dicts.append({
                'trade_id':None,
                'fee': Money(0, 'USD'),
                'btc': trade.volume,
                'fiat': fiat_trade
            })
        btc_total = sum([t.volume for t in trades], Money(0, 'BTC'))
        order_type = order.type
        order_details = {
            'btc_total': btc_total,
            'fiat_total': fiat_total,
            'trades': trades_dicts,
            'type': order_type
        }
        return order_details
    
    def multi_order_details_req(self):
        return None
    
    def multi_order_details_resp(self, req, order_ids):
        data = {}
        for oid in order_ids:
            self.order_details_req(oid)
            data[oid] = self.order_details_resp()
        return data

    def cancel_order_req(self, order_id):
        return self.engine.cancel_order(order_id)

    def cancel_order_resp(self, req):
        return {'success': True}


