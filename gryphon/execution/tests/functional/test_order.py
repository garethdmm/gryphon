import pyximport; pyximport.install()

import os
import unittest
import mock
from delorean import Delorean

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money

from gryphon.lib.models.order import Order

import logging
logger = logging.getLogger(__name__)

class TestOrder():

    def setUp(self):
        self.exchange = mock.Mock()
        self.order = Order('Test', Order.BID, Money("1", 'BTC'), Money("500", 'USD'), self.exchange, None)
        self.trade = {'btc': Money("0.1", 'BTC'),
            'trade_id': None,
            'fiat': Money("50", 'USD'),
            'fee': Money("1", 'USD'),
            'time': Delorean().epoch}
        self.order_details = {'btc_total': Money("0.1", 'BTC'),
            'trades': [self.trade],
            'type': Consts.BID,
            'fee': Money(0, 'USD'),
            'fiat_total': Money("50", 'USD')
            }
        pass

    def test_partially_eaten(self):
        positions, __ = self.order.was_partially_eaten(self.order_details)
        logger.debug(positions)
        btc_change = positions['BTC']
        fiat_change = positions['USD']
        btc_change.should.equal(Money("0.1", 'BTC'))
        fiat_change.should.equal(Money("-51", 'USD'))

        self.order.status.should.equal(Order.OPEN)
        self.order.trades.should.have.length_of(1)
        self.order.trades[0].volume.should.equal(Money("0.1", 'BTC'))

        self.order.volume_filled.should.equal(Money("0.1", 'BTC'))
        self.order.volume_remaining.should.equal(Money("0.9", 'BTC'))

    def test_partially_eaten_then_eaten(self):
        positions, __ = self.order.was_partially_eaten(self.order_details)
        btc_change = positions['BTC']
        fiat_change = positions['USD']
        btc_change.should.equal(Money("0.1", 'BTC'))
        fiat_change.should.equal(Money("-51", 'USD'))

        # order got cancelled
        positions, __ = self.order.was_eaten(self.order_details)
        btc_change = positions['BTC']
        fiat_change = positions['USD']

        # position should not change
        btc_change.should.equal(Money("0", 'BTC'))
        fiat_change.should.equal(Money("0", 'USD'))

    def test_multiple_partial_eats(self):
        order_details = self.order_details
        for i in range(3):
            positions, __ = self.order.was_partially_eaten(order_details)
            btc_change = positions['BTC']
            fiat_change = positions['USD']
            btc_change.should.equal(Money("0.1", 'BTC'))
            fiat_change.should.equal(Money("-51", 'USD'))
            order_details['trades'].append(self.trade)
            order_details['btc_total'] += Money("0.1", 'BTC')
            order_details['fiat_total'] += Money("50", 'USD')


        # order gets cancelled before we have a chance to "partially eat" the last change
        positions, __ = self.order.was_eaten(self.order_details)
        btc_change = positions['BTC']
        fiat_change = positions['USD']

        # position should reflect the one last change
        btc_change.should.equal(Money("0.1", 'BTC'))
        fiat_change.should.equal(Money("-51", 'USD'))

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
