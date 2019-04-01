"""
Just a few exercises for the execution configuration helper library.
"""

import pyximport; pyximport.install()
import os
import time
import unittest
import sure

from cdecimal import Decimal

from gryphon.execution.lib import config_helper
from gryphon.lib.money import Money


class TestConfiguration(unittest.TestCase):
    def test_cl_none_doesnt_override_conf_file(self):
        conf_file = {
            'platform': {'audit': True},
            'strategy': {'tick_sleep': 1},
        }

        command_line = {
            'platform': {'audit': None},
            'strategy': {'tick_sleep': None},
        }

        output = config_helper.combine_file_and_command_line_config(
            conf_file,
            command_line,
        )

        assert conf_file['platform']['audit'] is True
        assert conf_file['strategy']['tick_sleep'] == 1

    def test_command_line_overrides_conf_file(self):
        conf_file = {
            'platform': {'audit': False},
            'strategy': {'tick_sleep': 1},
        }

        command_line = {
            'platform': {'audit': True},
            'strategy': {'tick_sleep': 2},
        }

        output = config_helper.combine_file_and_command_line_config(
            conf_file,
            command_line,
        )

        assert conf_file['platform']['audit'] is True
        assert conf_file['strategy']['tick_sleep'] == 2

    def test_combine_works(self):
        conf_file = {
            'platform': {'audit': True},
            'strategy': {'spread': Decimal('0.10')},
        }

        command_line = {
            'platform': {'sentry': True},
            'strategy': {'tick_sleep': None},
        }

        output = config_helper.combine_file_and_command_line_config(
            conf_file,
            command_line,
        )

        assert conf_file['platform']['audit'] is True
        assert conf_file['platform']['sentry'] is True
        assert conf_file['strategy']['spread'] == Decimal('0.10')
        assert conf_file['strategy']['tick_sleep'] is None


    def test_parse_extra_args(self):
        extra_args = ['--spread', '0.01']

        parsed = config_helper.parse_extra_strategy_args(extra_args)

        assert len(parsed.keys()) == 1
        assert parsed.keys()[0] == 'spread'
        assert parsed['spread'] == Decimal('0.01')

    def test_parse_extra_args_boolean(self):
        extra_args = ['--market_order']

        parsed = config_helper.parse_extra_strategy_args(extra_args)

        assert len(parsed.keys()) == 1
        assert parsed.keys()[0] == 'market_order'
        assert parsed['market_order'] == True

    def test_parse_extra_args_complex(self):
        extra_args = [
            '--spread', '0.1',
            '--market_order',
            '--exchange', 'bitstamp',
            '--volume', 'BTC 1.0',
        ]

        parsed = config_helper.parse_extra_strategy_args(extra_args)

        assert len(parsed.keys()) == 4
        assert parsed['spread'] == Decimal('0.1')
        assert parsed['market_order'] == True
        assert parsed['exchange'] == 'bitstamp'
        assert parsed['volume'] == Money('1.0', 'BTC')

    def test_standardization(self):
        base_config = {}

        new_config = config_helper.format_file_config_to_standard(base_config)

        new_config.should.equal({'platform': {}, 'strategy': {}, 'exchanges': {}})

    def test_standardization_trivial(self):
        base_config = {
            'platform': {'audit': False},
        }

        new_config = config_helper.format_file_config_to_standard(base_config)

        new_config.should.equal(
            {'platform': {'audit': False}, 'strategy': {}, 'exchanges': {}}
        )

    def test_standardization_simple(self):
        base_config = {
            'platform': {'audit': False},
            'strategy': {'tick_sleep': Decimal('1')},
        }

        new_config = config_helper.format_file_config_to_standard(base_config)

        set(new_config.keys()).should.equal(set(['platform', 'strategy', 'exchanges']))
        new_config['platform']['audit'].should.equal(False)
        new_config['strategy']['tick_sleep'].should.equal(Decimal('1'))
        new_config['exchanges'].should.equal({})

    def test_standardization_exchanges(self):
        base_config = {
            'platform': {'audit': False},
            'strategy': {'tick_sleep': Decimal('1')},
            'coinbase_btc_usd': {'fiat_balance_tolerance': Money('0.01', 'USD')}
        }

        new_config = config_helper.format_file_config_to_standard(base_config)

        len(new_config['exchanges']).should.equal(1)
        len(new_config['exchanges']['coinbase_btc_usd'].keys()).should.equal(1)
        new_config['exchanges']['coinbase_btc_usd']['fiat_balance_tolerance']\
            .should.equal(Money('0.01', 'USD'))
