"""
"""
import pyximport; pyximport.install()
import os

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.fury.harness.exchange_coordinator import ExchangeCoordinator
from gryphon.tests.logic.exchange_coordinator.public_methods import ExchangePublicMethodsTests
from gryphon.tests.logic.exchange_coordinator.auth_methods import ExchangeAuthMethodsTests
from gryphon.lib.session import get_a_mysql_session
from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange import order_types
from gryphon.lib.models.order import Order


class TestKrakentExchangeCoordinator():
    def __init__(self):
        self.order1_price_amount = '10'
        self.order2_price_amount = '11'
        self.sleep_time = 1

    def setUp(self):
        self.db = get_a_mysql_session(creds=os.environ['TEST_DB_CRED'])
        self.exchange = ExchangeCoordinator(KrakenBTCEURExchange(), self.db)

    def tearDown(self):
        time.sleep(5)
        self.exchange.exchange_wrapper.cancel_all_open_orders()

    def test_order_placement(self):
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

        self.db.commit()

        assert result['success'] is True
        order1_exchange_order_id = result['order_id'] 

        db_order = self.db.query(Order)\
            .filter(Order.exchange_order_id == order1_exchange_order_id)\
            .first()

        assert db_order is not None
        assert db_order.exchange_order_id == order1_exchange_order_id
        assert db_order.status == 'OPEN'
        assert db_order.volume == order_volume
        assert db_order.price ==  order1_price





