"""
Just a few exercises for our configuration library.
"""
import pyximport; pyximport.install()
import os
import time

from cdecimal import Decimal

from gryphon.execution.lib import config_helper
from gryphon.lib.money import Money
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange


class BaseConfiguration(object):
    def __init__(self, *args, **kwargs):
        super(BaseConfiguration, self).__init__(*args, **kwargs)
        self.unconfigured_exchange_object = self.exchange_class()
        self.exchange_name = self.unconfigured_exchange_object.name.lower()
        self.volume_currency = self.unconfigured_exchange_object.volume_currency
        self.price_currency = self.unconfigured_exchange_object.currency

    def test_simple(self):
        configuration = {
            'platform': {'emerald': True},
            'strategy': {},
            'exchanges': {
                self.exchange_name: {
                    'fiat_balance_tolerance': Money('1', self.price_currency),
                },
            }
        }
      
        exchange = self.exchange_class(configuration=configuration)

        assert exchange.fiat_balance_tolerance == Money('1', self.price_currency)
        assert exchange.use_cached_orderbook == True

    def test_emerald_config_override(self):
        configuration = {
            'platform': {'emerald': False},
            'strategy': {},
            'exchanges': {
                self.exchange_name: {
                    'emerald': True,
                },
            },
        }

        exchange = self.exchange_class(configuration=configuration)

        assert exchange.use_cached_orderbook == True

    def test_no_config_goes_to_defaults(self):
        configuration = {
            'platform': {},
            'strategy': {},
        }

        exchange = self.exchange_class(configuration=configuration)

        assert exchange.use_cached_orderbook == False
        assert exchange.market_order_fee == self.DEFAULT_MARKET_FEE
        assert exchange.fiat_balance_tolerance == self.DEFAULT_FIAT_TOLERANCE
        assert exchange.volume_balance_tolerance == self.DEFAULT_VOLUME_TOLERANCE

    def test_all(self):
        configuration = {
            'platform': {'emerald': True},
            'strategy': {},
            'exchanges': {
                self.exchange_name: {
                    'market_order_fee': Decimal('0.1134'),
                    'limit_order_fee': Decimal('0.5911'),
                    'fiat_balance_tolerance': Money('1.032', self.price_currency),
                    'volume_balance_tolerance': Money('2.221', self.volume_currency),
                    'min_order_size': Money('442', self.volume_currency),
                    'emerald': False,
                    'max_tick_speed': 33215,
                },
            },
        }

        exchange = self.exchange_class(configuration=configuration)

        assert exchange.market_order_fee == Decimal('0.1134')
        assert exchange.limit_order_fee == Decimal('0.5911')
        assert exchange.fiat_balance_tolerance == Money('1.032', self.price_currency)
        assert exchange.volume_balance_tolerance == Money('2.221', self.volume_currency)
        assert exchange.min_order_size == Money('442', self.volume_currency)
        assert exchange.use_cached_orderbook == False
        assert exchange.max_tick_speed == 33215
