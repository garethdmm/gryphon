"""
Tests authenticated and order-placing endpoints.
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import logging
import os
import unittest
import sure
import mock
from mock import patch
import time

from gryphon.lib.money import Money
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.consts import Consts

logger = logging.getLogger(__name__)


class LiveOrdersTest(object):
    def __init__(self):
        self.order1_price_amount = '0.01'
        self.order2_price_amount = '0.02'
        self.sleep_time = 1

    def tearDown(self):
        try:
            self.exchange.cancel_all_open_orders()
            pass
        except:
            logger.error('Could not wind down, there may still be open orders.')

    def test_order_placement_status_and_cancel_methods(self):
        """
        This is a large test that exercises several elements of the wrapper at once,
        because otherwise there would be a lot of duplication between multiple test
        cases. Test here are place_order, get_open_orders, get_order_details,
        get_multi_order_details, cancel_order, and cancel_all_open_orders.
        """

        order_volume = Money('1', self.exchange.volume_currency)
        order1_price = Money(self.order1_price_amount, self.exchange.currency)
        order2_price = Money(self.order2_price_amount, self.exchange.currency)

        # Test the place_order function.

        result = self.exchange.place_order(
            mode=Consts.BID,
            volume=order_volume,
            price=order1_price,
            order_type=order_types.LIMIT_ORDER,
        )

        assert result['success'] is True
        order1_id = result['order_id'] 

        time.sleep(self.sleep_time)

        # Test that place_order had the expected affect through the get_open_orders()
        # function.

        open_orders = self.exchange.get_open_orders()

        assert len(open_orders) == 1
        assert open_orders[0]['id'] == order1_id
        assert open_orders[0]['price'] == order1_price
        assert open_orders[0]['volume_remaining'] == order_volume
      
        time.sleep(self.sleep_time)

        # Test the get_order_details function.

        order_details = self.exchange.get_order_details(order1_id)
        # Due to implementation sometimes get_order_details doesn't have the mode on it.
        assert order_details['type'] in [Consts.BID, None]
        assert order_details['fiat_total'] == Money('0', self.exchange.currency)
        assert len(order_details['trades']) == 0

        time.sleep(self.sleep_time)

        # Place a second order to test other functions.

        result = self.exchange.place_order(
            mode=Consts.BID,
            volume=order_volume,
            price=order2_price,
            order_type=order_types.LIMIT_ORDER,
        )

        assert result['success'] is True
        order2_id = result['order_id'] 

        time.sleep(self.sleep_time)

        # Test that both orders are now in open_orders.

        open_orders = self.exchange.get_open_orders()

        assert len(open_orders) == 2
        assert open_orders[0]['id'] in [order1_id, order2_id]

        time.sleep(self.sleep_time)

        # Test the get_multi_order_details function.

        multi_details = self.exchange.get_multi_order_details([order1_id, order2_id])

        assert len(multi_details) == 2
        assert order1_id in multi_details.keys() and order2_id in multi_details.keys()
        assert 'trades' in multi_details[order2_id]
        assert 'type' in multi_details[order2_id]
        assert 'fiat_total' in multi_details[order2_id]

        time.sleep(self.sleep_time)

        # Test cancelling an order and confirm the expected effect with get_open_orders.
        result = self.exchange.cancel_order(order1_id)

        time.sleep(self.sleep_time)

        open_orders = self.exchange.get_open_orders()

        assert len(open_orders) == 1
        assert open_orders[0]['id'] == order2_id

        # Test cancel_all_open_orders and confirm the expected effect with
        # get_open_orders.
        self.exchange.cancel_all_open_orders()

        time.sleep(self.sleep_time)

        open_orders = self.exchange.get_open_orders()

        assert len(open_orders) == 0

