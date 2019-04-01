import pyximport; pyximport.install()

import unittest
from decimal import Decimal

import logging
logger = logging.getLogger(__name__)

from gryphon.lib.exchange.sim_exchange import SimExchange
from backtesting.engine import Engine
from backtesting.orderflow_generator.regimes import RegimeBasedGenerator
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.money import Money

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.exchange = SimExchange(engine=Engine(RegimeBasedGenerator(1)))
    def tearDown(self):
        pass

    """
        Instantiating SimExchange should create an engine as well
    """
    def test_create_engine(self):
        self.assertTrue(self.exchange.engine != None)

    """
        A single call to get_orderbook should increase the size of the 
        orderbook to one, and the next call should increase it to two.
    """
    def test_get_orderbook_creates_an_order(self):
        orderbook = self.exchange.get_order_book()

        orderbook_size = len(orderbook.get('bids')) + len (orderbook.get('asks'))

        self.assertTrue(orderbook_size == 1)
      
        new_orderbook = self.exchange.get_order_book()

        new_orderbook_size = len(new_orderbook.get('bids')) + len(new_orderbook.get('asks'))

        self.assertTrue(new_orderbook_size == 2)


    """
      With the default seed value, fill_order_book should leave the
      test exchange with 73 orders on its books. If this has changed
      unexpectedly, we should know about it. Based on Baseline config 1
    """
    def test_fill_order_book_behaviour_has_not_changed(self):
        self.exchange.fill_order_book()

        orderbook = self.exchange.get_order_book()

        bids = orderbook.get('bids')
        asks = orderbook.get('asks')
        self.assertTrue(len(bids) + len(asks) == 73)
   
 

    """
        If we set a bid at the same price as an ask, those two orders
        should be matched and executed by our exchange engine.

        This only works because we know that the first order that is 
        generated based on the current random seed.
    """
    def test_buy_order_should_match(self):
        orderbook = self.exchange.get_order_book()

        ask = orderbook.get('asks', [])[0]

        order_response = self.exchange.create_trade(Order.BID, ask.volume, ask.price)

        order_id = order_response.get('order_id')

        statuses = self.exchange.multi_order_status([order_id])

        # there should only be one status here
        self.assertTrue(len(statuses) == 1)

        for order_id in statuses.keys():
            self.assertTrue(statuses[order_id]['status'] == 'filled')


    """
        If we set a bid at a price much lower than the initial ask, it
        should not be matched or executed in our exchange engine
    """
    def test_buy_order_should_not_match(self):
        orderbook = self.exchange.get_order_book()

        ask = orderbook.get('asks', [])[0]

        order_response = self.exchange.create_trade(
            Order.BID, 
            ask.volume, 
            ask.price - 2,
        )

        order_id = order_response.get('order_id')

        statuses = self.exchange.multi_order_status([order_id])

        # there should only be one status here
        self.assertTrue(len(statuses) == 1)
        
        logger.error(statuses)
        
        for order_id in statuses.keys():
            self.assertTrue(statuses[order_id]['status'] == 'open')


    """
        If we buy bitcoins, our fiat account balance should change by the
        appropriate amount in our exchange engine.
    """
    def test_account_balance_changes_after_buy(self):
        balances = self.exchange.balance()

        orderbook = self.exchange.get_order_book()

        ask = orderbook.get('asks', [])[0]

        order_response = self.exchange.create_trade(
            Order.BID, 
            ask.volume, 
            ask.price,
        )

        new_balances = self.exchange.balance()

        self.assertTrue(balances['BTC'] < new_balances['BTC'])
        self.assertTrue(balances['USD'] > new_balances['USD'])

    
    """
        If we create many trades, these trades should be returned by the
        exchange engine from an exchange.open_orders() call
    """
    def test_open_orders(self):
        for i in range(0,5):
            order_response = self.exchange.create_trade(
                Order.BID, 
                Money(1, 'BTC'),
                Money('500', 'USD'),
            )

        open_orders = self.exchange.open_orders()

        self.assertTrue(len(open_orders) == 5)

   
    """
        Test that the order_details function (which is poorly named because
        it is actually querying trades the relate to an order, not just
        the details of that order), is properly working.
    """ 
    def test_order_details(self):
        # create an absurdly high bid
        order_response = self.exchange.create_trade(
            Order.BID, 
            Money(1, 'BTC'),
            Money('100000', 'USD'),
        )
        
        order_id = order_response.get('order_id')

        order_details = self.exchange.order_details(order_id)
        logger.debug(order_details)

        # there's nothing in the order book yet so this should not have
        # matched
        self.assertTrue(len(order_details['trades']) == 0)
        
        self.exchange.fill_order_book()
        orderbook = self.exchange.get_order_book()
        
        new_order_details = self.exchange.order_details(order_id)

        # the high bid should have matched with new ask in the orderbook
        # so there should be trades in this order details
        self.assertTrue(len(new_order_details['trades']) > 0)


    """
        If we create an order and then cancel it, it should no longer
        appear in the results of an open_orders call.
    """
    def test_cancel_order(self):
        order_response = self.exchange.create_trade(
            Order.BID, 
            Money('1', 'BTC'),
            Money('100000', 'USD'),
        )

        order_id = order_response.get('order_id')

        open_orders = self.exchange.open_orders()

        self.assertTrue(len(open_orders) == 1)

        self.exchange.cancel_order(order_id)

        open_orders = self.exchange.open_orders()

        self.assertTrue(len(open_orders) == 0)


    """
        If we create many orders, they should all be present in the results
        of a exchange.multi_order_status call
    """
    def test_multi_order_status_req(self):
        order_ids = []

        for i in range(0,5):
            order_response = self.exchange.create_trade(
                Order.BID, 
                Money('1', 'BTC'),
                Money('1000', 'USD'),
            )

            order_ids.append(order_response['order_id'])

        order_statuses = self.exchange.multi_order_status(order_ids)

        self.assertTrue(len(order_statuses) == 5)

        for order_id in order_statuses.keys():
            order_status = order_statuses[order_id]['status']
            self.assertTrue(order_status == 'open')
    

