"""
"""
import pyximport; pyximport.install()
import os
import time
import unittest

from gryphon.fury.utils import audit
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.fury.harness.exchange_coordinator import ExchangeCoordinator
from gryphon.lib.session import get_a_mysql_session
from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange import order_types
from gryphon.lib.models.order import Order


class TestBitstampBTCUSDExchangeCoordinator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestBitstampBTCUSDExchangeCoordinator, self).__init__(*args, **kwargs)

        self.db = get_a_mysql_session(creds=os.environ['TEST_DB_CRED'])
        self.exchange = ExchangeCoordinator(BitstampBTCUSDExchange(), self.db)

        self.order1_price_amount = '6'
        self.order2_price_amount = '7'

        self.order_volume = Money('1', self.exchange.volume_currency)
        self.order1_price = Money(self.order1_price_amount, self.exchange.currency)
        self.order2_price = Money(self.order2_price_amount, self.exchange.currency)

        self.sleep_time = 1

    def setUp(self):
        # Make sure there's no open orders on the exchange.
        assert self.exchange.get_open_orders() == []

        # Cancel any orders in the db that were left over from previous tests.
        self._db_cancel_open_orders()

    def tearDown(self):
        time.sleep(self.sleep_time)

        self.exchange.exchange_wrapper.cancel_all_open_orders()

        self._db_cancel_open_orders()

    # Tests. #

    def test_accounting_cancelled_order(self):
        """
        Create an order the ExchangeCoordinator::place_order, then cancel it on the
        exchange and run accounting. Verify that it gets cancelled in the db and there
        are no effects to the position of the exchange account in our db.
        """

        exchange_account = self.exchange.exchange_account_db_object(self.db)
        initial_position = exchange_account.position.copy()

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 
       
        self.exchange.cancel_order(order1_exchange_order_id)

        time.sleep(2)
 
        open_orders = self.exchange.get_open_orders()
        eaten_order_ids, current_orders = self.exchange._get_current_orders(open_orders)
        self.exchange._run_accounting(eaten_order_ids, current_orders)

        # TODO: Run some asserts here that verify the thing was done.
        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        new_exchange_account = self.exchange.exchange_account_db_object(self.db)
        new_position = new_exchange_account.position.copy()

        assert db_order.status == Order.CANCELLED
        assert initial_position == new_position

    def test_accounting_untouched_open_order(self):
        """
        Test that if we place an order on the exchange and leave it there,
        run_accounting won't mess with it in our db.
        """

        exchange_account = self.exchange.exchange_account_db_object(self.db)
        initial_position = exchange_account.position.copy()

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 
       
        time.sleep(2)
 
        open_orders = self.exchange.get_open_orders()
        eaten_order_ids, current_orders = self.exchange._get_current_orders(open_orders)

        assert len(eaten_order_ids) == 0
        assert len(current_orders) == 1
        assert order1_exchange_order_id == current_orders[0]['id']

        self.exchange._run_accounting(eaten_order_ids, current_orders)

        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        new_exchange_account = self.exchange.exchange_account_db_object(self.db)
        new_position = new_exchange_account.position.copy()

        assert db_order.status == Order.OPEN
        assert initial_position == new_position

    def test_accounting_tick_flow(self):
        """
        Test that we can just get through the accounting flow code-path without issue.
        """
        open_orders = self.exchange.get_open_orders()

        eaten_order_ids, current_orders = self.exchange._get_current_orders(open_orders)

        self.exchange._run_accounting(eaten_order_ids, current_orders)

    # Accounting tests TODO:
    #   - a partially filled order that is now cancelled
    #   - a fully filled order
    #   - a partially filled order that is still on the books

    def test_handle_unexpected_orders_1(self):
        """
        Case 1: skip the ExchangeCoordinator object to directly place an order on the
        exchange and make sure that we raise the appropriate exception.
        """
        result = self.exchange.exchange_wrapper.place_order(
            mode=Consts.BID,
            volume=self.order_volume,
            price=self.order1_price,
            order_type=order_types.LIMIT_ORDER,
        )

        exchange_open_orders = self.exchange.get_open_orders()

        # With no db representation of this order, we should raise an exception.
        self.assertRaisesRegexp(
            audit.AuditException,
            'Unexpected Orders \(not in db\):',
            self.exchange._get_current_orders,
            exchange_open_orders,
        )

    def test_handle_unexpected_orders_2(self):
        """
        Case 2: place an order through ExchangeCoordinator, manipulate it to a FILLED
        state in the database, and make sure we raise the appropriate exception.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        # Account the order as 'filled'
        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        db_order.status = Order.FILLED
        self.db.add(db_order)
        self.db.commit()

        # Double check it got in there.
        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        assert db_order.status == Order.FILLED

        # Verify thet get_current_orders raises an exception.
        exchange_open_orders = self.exchange.get_open_orders()

        self.assertRaisesRegexp(
            audit.AuditException,
            'Unexpected Orders \(shouldn\'t be in open state on exchange\):',
            self.exchange._get_current_orders,
            exchange_open_orders,
        )

        # Ugly cleanup.
        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        db_order.status = Order.OPEN
        self.db.add(db_order)
        self.db.commit()

    def test_handle_unexpected_orders_3(self):
        """
        Case 3: place an order on the exchange and cancel it in our database. Assert
        That after get_current_orders the order is open in our database again.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        db_order.status = Order.CANCELLED
        self.db.add(db_order)
        self.db.commit()

        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]
        assert db_order.status == Order.CANCELLED

        exchange_open_orders = self.exchange.get_open_orders()
        self.exchange._get_current_orders(exchange_open_orders)
        self.db.commit()  # Have to force commit here since we're not in a tick.
        
        # Since the order was cancelled in the database, but open on the exchange,
        # handle_unexpected should have triggered re-cancelling logic, which just
        # assumes a previous request failed and tries again.
        db_order = self.exchange._get_orders_by_order_ids([order1_exchange_order_id])[0]

        assert db_order.status == Order.OPEN

    def test_get_current_orders(self):
        """
        I'm pretty sure the thing to do here is to make two orders, cancel one, then
        run _get_current, and make sure the cancelled order is in eaten_order_ids, and
        the open order is in current_orders.

        You could also set up a situation where this tests the handle_unexpected case.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        result = self._place_simple_order_2()

        assert result['success'] is True
        order2_exchange_order_id = result['order_id'] 

        self.exchange.cancel_order(order1_exchange_order_id)

        exchange_open_orders = self.exchange.get_open_orders()

        eaten_order_ids, current_orders = self.exchange._get_current_orders(
            exchange_open_orders,
        )

        assert len(current_orders) == 1
        assert len(eaten_order_ids) == 1
        assert order1_exchange_order_id in eaten_order_ids
        assert current_orders[0]['id'] == order2_exchange_order_id

    def test_db_open_orders(self):
        """
        Place on order through ExchangeCoordinator::place_order and verify that it's in
        the response of _get_db_open_orders.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        db_open_orders = self.exchange._get_db_open_orders()

        assert len(db_open_orders) == 1
        assert db_open_orders[0].exchange_order_id == order1_exchange_order_id

    def test_get_orders_by_ids(self):
        """
        Place on order through ExchangeCoordinator::place_order and verify that it's in
        the response of ExchangeCoordinator::_get_orders_by_order_ids.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        result = self._place_simple_order_2()

        assert result['success'] is True
        order2_exchange_order_id = result['order_id'] 

        orders = self.exchange._get_orders_by_order_ids([
            order1_exchange_order_id,
            order2_exchange_order_id,
        ])

        db_oids = [o.exchange_order_id for o in orders]

        assert len(orders) == 2
        assert order1_exchange_order_id in db_oids
        assert order2_exchange_order_id in db_oids

    def test_order_placement(self):
        """
        Test the place_order function.
        """

        result = self._place_simple_order_1()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        db_order = self.db.query(Order)\
            .filter(Order.exchange_order_id == order1_exchange_order_id)\
            .first()

        assert db_order is not None
        assert db_order.exchange_order_id == order1_exchange_order_id
        assert db_order.status == 'OPEN'
        assert db_order.volume == self.order_volume
        assert db_order.price == self.order1_price

    # Helper functions. #

    def _place_simple_order_1(self):
        """
        Simple helper function to place one common order on the exchange.
        """
        result = self.exchange.place_order(
            mode=Consts.BID,
            volume=self.order_volume,
            price=self.order1_price,
            order_type=order_types.LIMIT_ORDER,
        )

        return result

    def _place_simple_order_2(self):
        """
        A companion to _1.
        """
        result = self.exchange.place_order(
            mode=Consts.BID,
            volume=self.order_volume,
            price=self.order2_price,
            order_type=order_types.LIMIT_ORDER,
        )

        return result

    def _db_cancel_open_orders(self):
        self.db.query(Order)\
            .filter(Order._exchange_name == self.exchange.name)\
            .filter(Order.status == Order.OPEN)\
            .update({Order.status: Order.CANCELLED})

        self.db.commit()
