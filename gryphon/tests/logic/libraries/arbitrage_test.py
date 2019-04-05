"""
Tests for gryphon.lib.arbitrage.

TODO:
  - Add more tests using full real orderbooks, likely with cassettes.
  - Use mock or some other approach to allow us to run tests that involve forex
    conversion without requireing an OXR account to do so. This is important so that
    we can test e.g. detecting arbitrage between USD and CAD priced orderbooks.
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import unittest
import sure

from cdecimal import Decimal, ROUND_TRUNC

from gryphon.lib import arbitrage
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook
from gryphon.lib.money import Money
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange


class TestArbLib(unittest.TestCase):
    def setUp(self):
        self.itbit = ItbitBTCUSDExchange()
        self.bitstamp = BitstampBTCUSDExchange()

        self.itbit.market_order_fee = 0
        self.bitstamp.market_order_fee = 0

        self.trivial = {'bids': [], 'asks': []}

    def tearDown(self):
        pass

    def basic_ob_1(self, price_currency='USD', vol_currency='BTC'):
        ex = self.itbit

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        volume = Money('1', vol_currency)

        bids2 = [
            Order(Money('598', price_currency), volume, ex, Consts.BID),
            Order(Money('550', price_currency), volume, ex, Consts.BID),
        ]

        asks2 = [
            Order(Money('599', price_currency), volume, ex, Consts.ASK),
            Order(Money('650', price_currency), volume, ex, Consts.ASK),
        ]

        return {'bids': bids2, 'asks': asks2}

    def basic_ob_2(self, price_currency='USD', vol_currency='BTC'):
        ex = self.bitstamp
        volume = Money('1', vol_currency)

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        bids1 = [
            Order(Money('600', price_currency), volume, ex, Consts.BID),
            Order(Money('550', price_currency), volume, ex, Consts.BID),
        ]

        asks1 = [
            Order(Money('601', price_currency), volume, ex, Consts.ASK),
            Order(Money('650', price_currency), volume, ex, Consts.ASK),
        ]

        return {'bids': bids1, 'asks': asks1}

    def more_ob_1(self, price_currency='USD', vol_currency='BTC'):
        ex = self.bitstamp
        volume = Money('1', vol_currency)

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        bids3 = [
            Order(Money('600', price_currency), volume, ex, Consts.BID),
            Order(Money('550', price_currency), volume, ex, Consts.BID),
        ]

        asks3 = [
            Order(Money('601', price_currency), volume, ex, Consts.ASK),
            Order(Money('650', price_currency), volume, ex, Consts.ASK),
        ]

        return {'bids': bids3, 'asks': asks3}

    def more_ob_2(self, price_currency='USD', vol_currency='BTC'):
        ex = self.itbit
        volume_1 = Money('1', vol_currency)
        volume_2 = Money('0.5', vol_currency)

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        bids4 = [
            Order(Money('598', price_currency), volume_1, ex, Consts.BID),
            Order(Money('550', price_currency), volume_1, ex, Consts.BID),
        ]

        asks4 = [
            Order(Money('599', price_currency), volume_2, ex, Consts.ASK),
            Order(Money('599.5', price_currency), volume_2, ex, Consts.ASK),
            Order(Money('650', price_currency), volume_1, ex, Consts.ASK),
        ]


        return {'bids': bids4, 'asks': asks4}

    def real_orderbook_1(self, price_currency='USD', vol_currency='BTC'):
        ex = self.bitstamp

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        def price(literal):
            return Money(literal, price_currency)

        def vol(literal):
            return Money(literal, vol_currency)

        bids = [
            Order(price('604.31'), vol('4.20600000'), ex, Consts.BID),
            Order(price('604.30'), vol('3.00000000'), ex, Consts.BID),
            Order(price('604.25'), vol('2.76500000'), ex, Consts.BID),
            Order(price('604.24'), vol('3.43900000'), ex, Consts.BID),
            Order(price('604.00'), vol('1.82278003'), ex, Consts.BID),
            Order(price('603.98'), vol('4.83394284'), ex, Consts.BID),
            Order(price('603.75'), vol('20.00000000'), ex, Consts.BID),
            Order(price('603.61'), vol('4.57000000'), ex, Consts.BID),
            Order(price('603.51'), vol('0.01615431'), ex, Consts.BID),
            Order(price('603.38'), vol('4.58980000'), ex, Consts.BID),
        ]

        asks = [
            Order(price('605.37'), vol('0.82039084'), ex, Consts.ASK),
            Order(price('605.41'), vol('1.07069908'), ex, Consts.ASK),
            Order(price('605.47'), vol('1.01762788'), ex, Consts.ASK),
            Order(price('605.50'), vol('10.00000000'), ex, Consts.ASK),
            Order(price('606.19'), vol('16.93200000'), ex, Consts.ASK),
            Order(price('606.20'), vol('10.00000000'), ex, Consts.ASK),
            Order(price('606.51'), vol('4.84167900'), ex, Consts.ASK),
            Order(price('606.85'), vol('4.00000000'), ex, Consts.ASK),
            Order(price('606.92'), vol('1.01000000'), ex, Consts.ASK),
            Order(price('606.98'), vol('10.97000000'), ex, Consts.ASK),
        ]

        return {'bids': bids, 'asks': asks}

    def real_orderbook_2(self, price_currency='USD', vol_currency='BTC'):
        ex = self.itbit

        ex.currency = price_currency
        ex.volume_currency = vol_currency

        def price(literal):
            return Money(literal, price_currency)

        def vol(literal):
            return Money(literal, vol_currency)

        bids = [
            Order(price('605.89'), vol('58.8556'), ex, Consts.BID),
            Order(price('605.61'), vol('1.1'), ex, Consts.BID),
            Order(price('605.54'), vol('6.87'), ex, Consts.BID),
            Order(price('605.36'), vol('1.6455'), ex, Consts.BID),
            Order(price('605.09'), vol('1.413'), ex, Consts.BID),
            Order(price('604.88'), vol('1.059'), ex, Consts.BID),
            Order(price('604.7'), vol('78.7946'), ex, Consts.BID),
            Order(price('604.63'), vol('1'), ex, Consts.BID),
            Order(price('604.41'), vol('25'), ex, Consts.BID),
            Order(price('604.37'), vol('1.5642'), ex, Consts.BID),
        ]

        asks = [
            Order(price('606.62'), vol('60.8689'), ex, Consts.ASK),
            Order(price('606.85'), vol('1.5'), ex, Consts.ASK),
            Order(price('607.06'), vol('6.88'), ex, Consts.ASK),
            Order(price('607.1'), vol('1.64'), ex, Consts.ASK),
            Order(price('607.32'), vol('1.465'), ex, Consts.ASK),
            Order(price('607.59'), vol('31.83'), ex, Consts.ASK),
            Order(price('607.6'), vol('1'), ex, Consts.ASK),
            Order(price('607.82'), vol('2'), ex, Consts.ASK),
            Order(price('607.88'), vol('81.9195'), ex, Consts.ASK),
            Order(price('607.98'), vol('0.34'), ex, Consts.ASK),
        ]

        return {'bids': bids, 'asks': asks}

    def test_trivial(self):
        result = arbitrage.detect_cross(self.trivial, self.trivial)

        result.should.equal(None)

    def test_basic(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """

        result = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        result.volume.should.equal(Money('1', 'BTC'))
        result.revenue.should.equal(Money('1', 'USD'))

    def test_mismatch(self):
        """
        Don't ask for cross information between two orderbooks with different volume
        currencies.
        """
        arbitrage.detect_cross.when.called_with(
            self.basic_ob_2(vol_currency='ETH'),
            self.basic_ob_1(),
        ).should.throw(
            arbitrage.MismatchedVolumeCurrenciesError,
        )

    def test_basic_non_btc(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """

        result = arbitrage.detect_cross(
            self.basic_ob_2(vol_currency='ETH'),
            self.basic_ob_1(vol_currency='ETH'),
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('1', 'USD'))

    def test_basic_crypto_crypto(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """

        result = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('1', 'BTC'))

    def test_basic_crypto_crypto_unprofitable(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """

        self.itbit.market_order_fee = Decimal('0.1')
        self.bitstamp.market_order_fee = Decimal('0.1')

        result = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        result.should.equal(None)

    def test_basic_crypto_crypto_minimally_profitable(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """
        self.itbit.market_order_fee = Decimal('0.0008')
        self.bitstamp.market_order_fee = Decimal('0.0008')

        result = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('1', 'BTC'))
        result.fees.should.equal(Money('0.9592', 'BTC'))
        result.profit.should.equal(Money('0.0408', 'BTC'))

    def test_basic_crypto_crypto_unprofitable_with_ignore_flag_off(self):
        """
        OB1 has a bid at 600 and OB2 has an ask at 599, both at 1btc. These should cross
        for a volume of 2btc and a profit of $1 USD.
        """

        self.itbit.market_order_fee = Decimal('0.1')
        self.bitstamp.market_order_fee = Decimal('0.1')

        result = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
            ignore_unprofitable=False,
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('1', 'BTC'))
        result.fees.should.equal(Money('119.9', 'BTC'))

    def test_commutative(self):
        """
        Same orderbooks as test_basic, double check it doesn't matter which order we
        give this function the orderbooks.
        """

        result = arbitrage.detect_cross(self.basic_ob_1(), self.basic_ob_2())

        result.volume.should.equal(Money('1', 'BTC'))
        result.revenue.should.equal(Money('1', 'USD'))

    def test_bigger(self):
        """
        OB1 has a bit at 600 which should cross at 599 for 0.5btc and 599.5 for 0.5 btc
        for a volume of 2btc and a profit of $0.75.
        """

        result = arbitrage.detect_cross(self.more_ob_1(), self.more_ob_2())

        result.volume.should.equal(Money('1', 'BTC'))
        result.revenue.should.equal(Money('0.75', 'USD'))

    def test_bigger_non_btc(self):
        """
        OB1 has a bit at 600 which should cross at 599 for 0.5btc and 599.5 for 0.5 btc
        for a volume of 2btc and a profit of $0.75.
        """

        result = arbitrage.detect_cross(
            self.more_ob_1(vol_currency='ETH'),
            self.more_ob_2(vol_currency='ETH'),
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('0.75', 'USD'))

    def test_bigger_crypto_crypto(self):
        """
        OB1 has a bit at 600 which should cross at 599 for 0.5btc and 599.5 for 0.5 btc
        for a volume of 2btc and a profit of $0.75.
        """

        result = arbitrage.detect_cross(
            self.more_ob_1(price_currency='BTC', vol_currency='ETH'),
            self.more_ob_2(price_currency='BTC', vol_currency='ETH'),
        )

        result.volume.should.equal(Money('1', 'ETH'))
        result.revenue.should.equal(Money('0.75', 'BTC'))

    def test_bigger_multi_fiat_price(self):
        """
        OB1 has a bit at 600 which should cross at 599 for 0.5btc and 599.5 for 0.5 btc
        for a volume of 2btc and a profit of $0.75.

        TODO:
          - in order to keep this test in the 'logic' we'll need to figure out how to
            use a mock in the forex library so we don't require an OXR account.
        """
        pass
        #result = arbitrage.detect_cross(
        #    self.more_ob_1(price_currency='USD', vol_currency='ETH'),
        #    self.more_ob_2(price_currency='CAD', vol_currency='ETH'),
        #)

        #result.volume.should.equal(Money('2', 'ETH'))
        # The revenue number will fluctuate with the exchange rate.

    def test_bigger_commutative(self):
        """
        Same as bigger, testing commutivity again.
        """

        result = arbitrage.detect_cross(self.more_ob_2(), self.more_ob_1())

        result.volume.should.equal(Money('1', 'BTC'))
        result.revenue.should.equal(Money('0.75', 'USD'))

    def test_real_data(self):
        """
        Test based on real data taken from itbit and bitstamp at about 4:30 on
        September 26 2016 against math done by hand.
        """

        result = arbitrage.detect_cross(
            self.real_orderbook_1(),
            self.real_orderbook_2(),
        )

        result.volume.should.equal(Money('12.9087178', 'BTC'))
        result.revenue.should.equal(Money('5.2679425048', 'USD'))

    def test_real_data_unprofitable(self):
        """
        Test based on real data taken from itbit and bitstamp at about 4:30 on
        September 26 2016 against math done by hand.
        """
        self.itbit.market_order_fee = Decimal('0.01')
        self.bitstamp.market_order_fee = Decimal('0.01')

        result = arbitrage.detect_cross(
            self.real_orderbook_1(),
            self.real_orderbook_2(),
        )

        result.should.equal(None)

    def test_real_data_unprofitable_flag_off(self):
        """
        Test based on real data taken from itbit and bitstamp at about 4:30 on
        September 26 2016 against math done by hand.
        """
        self.itbit.market_order_fee = Decimal('0.10')
        self.bitstamp.market_order_fee = Decimal('0.10')

        result = arbitrage.detect_cross(
            self.real_orderbook_1(),
            self.real_orderbook_2(),
            ignore_unprofitable=False,
        )

        result.volume.should.equal(Money('12.9087178', 'BTC'))
        result.revenue.should.equal(Money('5.2679425048', 'USD'))
        assert result.profit < Money('0', 'USD')

    def test_real_data_non_btc(self):
        """
        Test based on real data taken from itbit and bitstamp at about 4:30 on
        September 26 2016 against math done by hand.
        """

        result = arbitrage.detect_cross(
            self.real_orderbook_1(vol_currency='ETH'),
            self.real_orderbook_2(vol_currency='ETH'),
        )

        result.volume.should.equal(Money('12.9087178', 'ETH'))
        result.revenue.should.equal(Money('5.2679425048', 'USD'))

    def test_real_data_crypto_crypto(self):
        """
        Test based on real data taken from itbit and bitstamp at about 4:30 on
        September 26 2016 against math done by hand.
        """

        result = arbitrage.detect_cross(
            self.real_orderbook_1(price_currency='BTC', vol_currency='ETH'),
            self.real_orderbook_2(price_currency='BTC', vol_currency='ETH'),
        )

        result.volume.should.equal(Money('12.9087178', 'ETH'))
        result.revenue.should.equal(Money('5.2679425048', 'BTC'))

    def test_real_data_directional(self):
        """
        Test that the directional calculations work as expected against real data.
        """

        result1 = arbitrage.detect_directional_cross(
            self.real_orderbook_1(),
            self.real_orderbook_2(),
        )

        result1.volume.should.equal(Money('12.9087178', 'BTC'))
        result1.revenue.should.equal(Money('5.2679425048', 'USD'))

        result2 = arbitrage.detect_directional_cross(
            self.real_orderbook_2(),
            self.real_orderbook_1(),
        )

        result2.should.equal(None)

    def test_cross_falsiness(self):
        cross = arbitrage.Cross(
            Money('0', 'BTC'),
            Money('0', 'USD'),
            Money('0', 'USD'),
        )

        falsiness = False

        if cross:
            falsiness = True

        falsiness.should.equal(False)

    def test_cross_truthiness(self):
        cross = arbitrage.Cross(
            Money('1', 'BTC'),
            Money('1', 'USD'),
            Money('1', 'USD'),
        )

        falsiness = False

        if cross:
            falsiness = True

        falsiness.should.equal(True)

    def test_cross_profit(self):
        cross = arbitrage.Cross(
            Money('1', 'BTC'),
            Money('1', 'USD'),
            Money('1', 'USD'),
        )

        cross.profit.should.equal(Money('0', 'USD'))

        cross = arbitrage.Cross(
            Money('1', 'BTC'),
            Money('3.3', 'USD'),
            Money('0.03', 'USD'),
        )

        cross.profit.should.equal(Money('3.27', 'USD'))

    def test_max_buy_zero(self):
        result = arbitrage.max_buy_volume(Money('0', 'USD'), self.basic_ob_1())

        result.should.equal(Money('0', 'BTC'))

    def test_max_buy_all(self):
        result = arbitrage.max_buy_volume(Money('10000', 'USD'), self.basic_ob_1())

        result.should.equal(Money('2', 'BTC'))

    def test_max_buy_one_order(self):
        result = arbitrage.max_buy_volume(Money('599', 'USD'), self.basic_ob_1())

        result.should.equal(Money('1', 'BTC'))

    def test_max_buy_half_order(self):
        result = arbitrage.max_buy_volume(Money('299.5', 'USD'), self.basic_ob_1())

        result.should.equal(Money('0.5', 'BTC'))

    def test_max_buy_one_five_order(self):
        result = arbitrage.max_buy_volume(Money('924', 'USD'), self.basic_ob_1())

        result.should.equal(Money('1.5', 'BTC'))

    def test_max_buy_fee_simple(self):
        self.itbit.market_order_fee = Decimal('1')

        result = arbitrage.max_buy_volume(Money('599', 'USD'), self.basic_ob_1())

        result.should.equal(Money('0.5', 'BTC'))

    def test_max_buy_fee_simple(self):
        self.itbit.market_order_fee = Decimal('0.1')

        result = arbitrage.max_buy_volume(Money('599', 'USD'), self.basic_ob_1())

        result.round_to_decimal_places(3, ROUND_TRUNC).should.equal(
            Money('0.909', 'BTC'),
        )

    def test_get_executable(self):
        cross = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('599', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('1', 'BTC'))

    def test_get_executable_no_buy_balance(self):
        cross = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('0', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0', 'BTC'))

    def test_get_executable_no_buy_balance_b(self):
        cross = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('0', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1000', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0', 'BTC'))

    def test_get_executable_no_sell_balance(self):
        cross = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('599', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('0', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0', 'BTC'))

    def test_get_executable_no_sell_balance_b(self):
        cross = arbitrage.detect_cross(self.basic_ob_2(), self.basic_ob_1())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('599', 'USD'), 'BTC': Money('1000000', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('0', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0', 'BTC'))

    def test_get_executable_crypto_crypto(self):
        cross = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        cross.volume.should.equal(Money('1', 'ETH'))
        cross.revenue.should.equal(Money('1', 'BTC'))

        buy_balance = {'BTC': Money('599', 'BTC'), 'ETH': Money('1000000', 'ETH')}
        sell_balance = {'BTC': Money('0', 'BTC'), 'ETH': Money('1', 'ETH')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('1', 'ETH'))

    def test_get_executable_half(self):
        cross = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        cross.volume.should.equal(Money('1', 'ETH'))
        cross.revenue.should.equal(Money('1', 'BTC'))

        buy_balance = {'BTC': Money('299.5', 'BTC'), 'ETH': Money('1000000', 'ETH')}
        sell_balance = {'BTC': Money('0', 'BTC'), 'ETH': Money('1', 'ETH')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0.5', 'ETH'))

    def test_get_executable_half(self):
        cross = arbitrage.detect_cross(
            self.basic_ob_2(price_currency='BTC', vol_currency='ETH'),
            self.basic_ob_1(price_currency='BTC', vol_currency='ETH'),
        )

        cross.volume.should.equal(Money('1', 'ETH'))
        cross.revenue.should.equal(Money('1', 'BTC'))

        buy_balance = {'BTC': Money('299.5', 'BTC'), 'ETH': Money('1000000', 'ETH')}
        sell_balance = {'BTC': Money('0', 'BTC'), 'ETH': Money('1', 'ETH')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0.5', 'ETH'))

    def test_get_executable_restriction(self):
        cross = arbitrage.detect_cross(self.more_ob_1(), self.more_ob_2())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('0.75', 'USD'))

        buy_balance = {'USD': Money('299.5', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0.5', 'BTC'))

    def test_get_executable_full_second_order(self):
        cross = arbitrage.detect_cross(self.more_ob_1(), self.more_ob_2())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('0.75', 'USD'))

        buy_balance = {'USD': Money('599.25', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('1', 'BTC'))

    def test_get_executable_partial_second_order(self):
        cross = arbitrage.detect_cross(self.more_ob_1(), self.more_ob_2())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('0.75', 'USD'))

        buy_balance = {'USD': Money('449.375', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0.75', 'BTC'))

    def test_get_executable_simple_fee(self):
        self.itbit.market_order_fee = 1
        self.bitstamp.market_order_fee = 1

        cross = arbitrage.detect_cross(
            self.basic_ob_2(),
            self.basic_ob_1(),
            ignore_unprofitable=False,
        )

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('599', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.should.equal(Money('0.5', 'BTC'))

    def get_test_executable_realistic_fee(self):
        self.itbit.market_order_fee = Decimal('0.0001')
        self.bitstamp.market_order_fee = Decimal('0.0001')

        cross = arbitrage.detect_cross(
            self.basic_ob_2(),
            self.basic_ob_1(),
            ignore_unprofitable=False,
        )

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('1', 'USD'))

        buy_balance = {'USD': Money('599', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.round_to_decimal_places(8).should.equal(Money('0.99990001', 'BTC'))

    def test_get_executable_fee_complex(self):
        self.itbit.market_order_fee = Decimal('0.0001')
        self.bitstamp.market_order_fee = Decimal('0.0001')

        cross = arbitrage.detect_cross(self.more_ob_1(), self.more_ob_2())

        cross.volume.should.equal(Money('1', 'BTC'))
        cross.revenue.should.equal(Money('0.75', 'USD'))

        buy_balance = {'USD': Money('599.25', 'USD'), 'BTC': Money('0', 'BTC')}
        sell_balance = {'USD': Money('0', 'USD'), 'BTC': Money('1', 'BTC')}

        result = arbitrage.get_executable_volume(cross, buy_balance, sell_balance)

        result.round_to_decimal_places(8, ROUND_TRUNC)\
            .should.equal(Money('0.99990005', 'BTC'))

    def test_get_many_simple(self):
        orderbooks = [self.basic_ob_2(), self.basic_ob_1()]

        crosses = arbitrage.detect_crosses_between_many_orderbooks(orderbooks)

        len(crosses).should.equal(1)

        crosses[0].volume.should.equal(Money('1', 'BTC'))
        crosses[0].revenue.should.equal(Money('1', 'USD'))

    def test_get_many_fees(self):
        self.bitstamp.market_order_fee = Decimal('0.01')

        orderbooks = [self.basic_ob_2(), self.basic_ob_1()]

        crosses = arbitrage.detect_crosses_between_many_orderbooks(orderbooks)

        len(crosses).should.equal(0)

    def test_get_many_fees_ignore_false(self):
        self.bitstamp.market_order_fee = Decimal('0.001')

        orderbooks = [self.basic_ob_2(), self.basic_ob_1()]

        crosses = arbitrage.detect_crosses_between_many_orderbooks(
            orderbooks,
            ignore_unprofitable=False,
        )

        len(crosses).should.equal(1)

    def test_get_many_two_crosses(self):
        orderbooks = [self.basic_ob_2(), self.basic_ob_2(), self.basic_ob_1()]

        crosses = arbitrage.detect_crosses_between_many_orderbooks(orderbooks)

        len(crosses).should.equal(2)
        crosses[0].volume.should.equal(Money('1', 'BTC'))
        crosses[0].revenue.should.equal(Money('1', 'USD'))
        crosses[1].volume.should.equal(Money('1', 'BTC'))
        crosses[1].revenue.should.equal(Money('1', 'USD'))

    def test_get_many_two_separate_crosses(self):
        orderbooks = [
            self.basic_ob_2(),
            self.basic_ob_1(),
            self.more_ob_2(),
            self.more_ob_1(),
        ]

        crosses = arbitrage.detect_crosses_between_many_orderbooks(orderbooks)

        len(crosses).should.equal(4)
        crosses[0].revenue.should.equal(Money('1', 'USD'))
        crosses[0].volume.should.equal(Money('1', 'BTC'))
        crosses[-1].volume.should.equal(Money('1', 'BTC'))
        crosses[-1].revenue.should.equal(Money('0.75', 'USD'))

