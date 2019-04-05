import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

from decimal import Decimal
import mock
import sure
import unittest

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.gryphonfury import positions
from gryphon.lib.gryphonfury import revenue as revenue_lib
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money


class TestProfit():
    def setUp(self):
        self.order = mock.MagicMock()
        self.order.exchange_rate = Decimal('0.80')
        self.order.fundamental_value = Money('250', 'USD')

        self.trades = []

        self.bid = Trade(
            Consts.BID,
            Money('100', 'USD'),
            Money('0', 'USD'),
            Money('1', 'BTC'),
            '1',
            self.order,
        )

        self.trades.append(self.bid)

        self.ask = Trade(
            Consts.ASK,
            Money('100', 'USD'),
            Money('0', 'USD'),
            Money('1', 'BTC'),
            '2',
            self.order,
        )

        self.trades.append(self.ask)

    def tearDown(self):
        pass

    def test_position_delta(self):
        position = positions.position_delta(self.trades)

        position['BTC'].should.equal(Money('0', 'BTC'))
        position['fiat'].should.equal(Money('0', 'USD'))

    def test_position_delta_with_fees(self):
        self.bid.fee = Money('1', 'USD')
        self.ask.fee = Money('2', 'USD')

        position = positions.position_delta(self.trades)

        position['BTC'].should.equal(Money('0', 'BTC'))
        position['fiat'].should.equal(Money('-3', 'USD'))

    def test_position_delta_with_btc_fees(self):
        self.bid.fee = Money('0.01', 'BTC')
        self.ask.fee = Money('0.02', 'BTC')

        position = positions.position_delta(self.trades)

        position['BTC'].should.equal(Money('0', 'BTC'))
        position['fiat'].should.equal(Money('-7.5', 'USD'))

    def test_split_trades(self):
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)

        # Expect to match all of #1 with #2 with no remaining position.
        matched_trades.should.have.length_of(2)
        matched_trades[0].volume.should.equal(Money('1', 'BTC'))
        matched_trades[1].volume.should.equal(Money('1', 'BTC'))

        position_trades.should.be.empty

    def test_split_trades_partial_matches(self):
        self.ask.volume = Money('0.25', 'BTC')

        new_ask = Trade(
            Consts.ASK,
            Money('100', 'USD'),
            Money('0', 'USD'),
            Money('2', 'BTC'),
            '3',
            self.order,
        )

        new_ask._exchange_rate = None
        self.trades.append(new_ask)
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)

        # expect to match:
        # 0.25 of #1 with all of #2
        # 0.75 of #1 with 0.75 of #3
        # with 1.25 of #3 left in position
        matched_trades.should.have.length_of(4)
        matched_trades[0].volume.should.equal(Money('0.25', 'BTC'))
        matched_trades[1].volume.should.equal(Money('0.25', 'BTC'))
        matched_trades[2].volume.should.equal(Money('0.75', 'BTC'))
        matched_trades[3].volume.should.equal(Money('0.75', 'BTC'))

        position_trades.should.have.length_of(1)
        position_trades[0].volume.should.equal(Money('1.25', 'BTC'))

    def test_split_trades_with_btc_fees(self):
        self.bid.fee = Money('0.01', 'BTC')

        matched_trades, position_trades = revenue_lib.split_trades(self.trades)

        # expect to match all of #1 with #2
        # with no remaining position
        matched_trades.should.have.length_of(2)
        matched_trades[0].volume.should.equal(Money('1', 'BTC'))
        matched_trades[1].volume.should.equal(Money('1', 'BTC'))

        position_trades.should.be.empty

    def test_profit_units(self):
        self.bid.price = Money('90', 'USD')
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)
        profit_units = revenue_lib.profit_units(matched_trades)
        profit_units.should.have.length_of(1)
        profit_units[0]['profit'].should.equal(Money('10', 'USD'))

    def test_profit_units_with_btc_fees(self):
        self.bid.fee = Money('0.01', 'BTC')
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)
        profit_units = revenue_lib.profit_units(matched_trades)

        profit_units.should.have.length_of(1)
        profit_units[0]['profit'].should.equal(Money('-2.50', 'USD'))

    def test_profit_units_with_btc_and_fiat_fees(self):
        self.bid.fee = Money('0.01', 'BTC')
        self.ask.fee = Money('1', 'USD')

        matched_trades, position_trades = revenue_lib.split_trades(self.trades)
        profit_units = revenue_lib.profit_units(matched_trades)

        profit_units.should.have.length_of(1)
        profit_units[0]['profit'].should.equal(Money('-3.50', 'USD'))

    def test_profit_units_with_btc_and_fiat_fees_and_cad(self):
        self.bid.volume = Money('1', 'BTC')
        self.bid.price = Money('100', 'CAD')
        self.bid.fee = Money('0.01', 'BTC')

        self.ask.volume = Money('1', 'BTC')
        self.ask.price = Money('101', 'CAD')
        self.ask.fee = Money('1', 'CAD')
        
        self.order.fundamental_value = Money(250, 'CAD')
        
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)
        profit_units = revenue_lib.profit_units(matched_trades)
        profit_units.should.have.length_of(1)
        profit_units[0]['profit'].should.equal(Money('-2.50', 'CAD'))
        
    def test_profit_with_btc_and_fiat_fees_and_cad(self):
        self.bid.volume = Money('1', 'BTC')
        self.bid.price = Money('100', 'CAD')
        self.bid.fee = Money('0.01', 'BTC')

        self.ask.volume = Money('1', 'BTC')
        self.ask.price = Money('101', 'CAD')
        self.ask.fee = Money('1', 'CAD')
        
        self.order.fundamental_value = Money(250, 'CAD')
    
        matched_trades, position_trades = revenue_lib.split_trades(self.trades)
        p = revenue_lib.realized_pl(matched_trades)

        p.should.equal(Money('-2.50', 'CAD'))

