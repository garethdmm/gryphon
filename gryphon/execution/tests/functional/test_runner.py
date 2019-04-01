import pyximport; pyximport.install()

import os
import unittest
import mock
from delorean import Delorean

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money

from algos.naive import Naive
from algos.harness import Harness
from gryphon.lib.models.order import Order
from gryphon.lib.models.exchange import Position, Balance
from brain import Brain

import logging
logger = logging.getLogger(__name__)

class TestHarness():

    def setUp(self):
        self.db = mock.Mock()

        self.algo = mock.Mock()
        self.algo.brain = Brain()

        exchange_data = mock.Mock()
        exchange_data.position = Position()
        exchange_data.balance = Balance()
        self.algo.exchange_data = exchange_data

        exchange = mock.Mock()
        exchange.name = "TestExchange"
        exchange.currency = "USD"
        exchange.get_order_book_resp = mock.Mock(return_value=None)
        exchange.exchange_data = mock.Mock(return_value=exchange_data)
        self.algo.exchange = exchange

        self.algo.params = {'fundamental_depth':Money(1, 'BTC')}

        self.algo.fundamental_exchanges = []

        # We have a 1 BTC bid for 500 on the book
        self.order = Order("Test", Consts.BID, Money("1", 'BTC'), Money("500", 'USD'), self.algo.exchange, '123')
        self.algo._get_open_orders = mock.Mock(return_value=[self.order])

        self.algo._get_orders_by_order_ids = mock.Mock(return_value=[self.order])

        self.harness = Harness(self.algo, self.db)

    def test_eaten_orders(self):
        # Our open order has been taken
        self.algo.exchange.open_orders = mock.Mock(return_value=[])
        self.algo.calc_fundamental_value = mock.Mock(return_value=Money('500', 'USD'))

        open_orders = self.harness.fetch_tick_data(None)
        eaten_order_ids, current_orders = self.harness.get_current_orders(open_orders)
        eaten_order_ids.should.have.length_of(1)
        eaten_order_ids.should.contain('123')
        current_orders.should.be.empty

    def test_current_orders(self):
        # our open order is still there
        self.algo.exchange.open_orders = mock.Mock(return_value=[{'id': '123'}])
        self.algo.calc_fundamental_value = mock.Mock(return_value=Money('500', 'USD'))

        open_orders = self.harness.fetch_tick_data(None)
        eaten_order_ids, current_orders = self.harness.get_current_orders(open_orders)
        eaten_order_ids.should.be.empty
        current_orders.should.have.length_of(1)
        current_orders[0].should.have.key('id').being.equal('123')

    def test_accounting(self):
        v = Money("1", 'BTC')
        p = Money("500", 'USD')

        # our open order was completely taken
        multi_order_details = {'123': {'btc_total': v,
          'trades': [{'btc': v,
            'trade_id': None,
            'fiat': p,
            'fee': Money('0', 'USD'),
            'time': Delorean().epoch,
            }],
          'type': Consts.BID,
          'fiat_total': p
          }}
        self.algo.exchange.multi_order_details = mock.Mock(return_value=multi_order_details)
        self.algo.fundamental_value = Money("500", 'USD')
        self.harness.run_accounting(['123'], [])
        self.algo.exchange_data.position['USD'].should.equal(Money("0", 'USD') - p)
        self.algo.exchange_data.position['BTC'].should.equal(v)

        self.order.status.should.equal("FILLED")

        self.order.trades.should.have.length_of(1)
        self.order.trades[0].volume.should.equal(v)
        self.order.trades[0].price.should.equal(p)

    def test_accounting_cancelled(self):
        v = Money("0", 'BTC')
        p = Money("0", 'USD')

        # our open order was cancelled
        multi_order_details = {'123': {'btc_total': v,
          'trades': [],
          'type': Consts.BID,
          'fiat_total': p,
          }}
        self.algo.exchange.multi_order_details = mock.Mock(return_value=multi_order_details)

        self.algo.fundamental_value = Money("500", 'USD')
        self.harness.run_accounting(['123'], [])
        self.algo.exchange_data.position['USD'].should.equal(Money("0", 'USD') - p)
        self.algo.exchange_data.position['BTC'].should.equal(v)

        self.order.status.should.equal("CANCELLED")

        self.order.trades.should.be.empty

    def test_accounting_partially_filled(self):
        v = Money("0.1", 'BTC')
        p = Money("50", 'USD')

        # our open order was partially
        order_details = {'123':{'btc_total': v,
          'trades': [{'btc': v,
            'trade_id': None,
            'fiat': p,
            'fee': Money('0', 'USD'),
            'time': Delorean().epoch,
            }],
          'type': Consts.BID,
          'fiat_total': p,
          }
         }
        self.algo.exchange.multi_order_details = mock.Mock(return_value=order_details)

        current_orders = [{'id': '123',
          'mode': Consts.BID,
          'price': Money("500", 'USD'),
          'volume_remaining': Money("0.9", 'BTC')}]

        self.algo.fundamental_value = Money("500", 'USD')
        self.harness.run_accounting([], current_orders)
        self.algo.exchange_data.position['USD'].should.equal(Money("0", 'USD') - p)
        self.algo.exchange_data.position['BTC'].should.equal(v)

        self.order.status.should.equal('OPEN')

        self.order.trades.should.have.length_of(1)
        self.order.trades[0].volume.should.equal(v)
        self.order.trades[0].price.should.equal(p)

    def test_accounting_partially_filled_then_cancelled(self):
        v = Money("0.1", 'BTC')
        p = Money("50", 'USD')

        # our open order was partially
        order_details = {'btc_total': v,
          'trades': [{'btc': v,
            'trade_id': None,
            'fiat': p,
            'fee': Money('0', 'USD'),
            'time': Delorean().epoch,
            }],
          'type': Consts.BID,
          'fiat_total': p,
          }
        multi_order_details = {'123': order_details}
        self.algo.exchange.order_details = mock.Mock(return_value=order_details)
        self.algo.exchange.multi_order_details = mock.Mock(return_value=multi_order_details)


        current_orders = [{'id': '123',
          'mode': Consts.BID,
          'price': Money("500", 'USD'),
          'volume_remaining': Money("0.9", 'BTC')}]
        self.algo.fundamental_value = Money("500", 'USD')
        self.harness.run_accounting([], current_orders)
        self.algo.exchange_data.position['USD'].should.equal(Money("0", 'USD') - p)
        self.algo.exchange_data.position['BTC'].should.equal(v)

        # order got cancelled
        self.harness.run_accounting(['123'], [])

        # position should not change
        self.algo.exchange_data.position['USD'].should.equal(Money("0", 'USD') - p)
        self.algo.exchange_data.position['BTC'].should.equal(v)

        # trades should not change
        self.order.trades.should.have.length_of(1)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
