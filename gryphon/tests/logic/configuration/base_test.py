"""
Tests for the gryphon.lib configuration library.
"""

import pyximport; pyximport.install()
import unittest
import mock
import sure

from cdecimal import Decimal

from gryphon.lib import configuration
from gryphon.lib.money import Money


TRIVIAL_CONFIG_FILE = """\
[strategy]
midpoint: 0.001
"""

SIMPLE_CONFIG_FILE = """\
[strategy]
midpoint: 0.001
quote_depth = BTC 20
use_gds: yes
primary_exchange_name: coinbase_btc_usd
"""

MULTISECTION_CONFIG_FILE = """\
[platform]
audit: no

[strategy]
tick_sleep: 1
"""

SUBSECTION_CONFIG_FILE = """\
[platform]
audit: no

[strategy]
tick_sleep: 1

[strategy:midpoint_weights]
coinbase_btc_usd: 0.5
bitstamp_btc_usd: 0.5
"""


class TestConfiguration(unittest.TestCase):
    def test_parse_list_simple(self):
        value = 'bitstamp'

        output = configuration.parse_configurable_as_list(value)
      
        len(output).should.equal(1)
        output[0].should.equal('bitstamp')

    def test_parse_list_more(self):
        value = 'bitstamp,coinbase,kraken'

        output = configuration.parse_configurable_as_list(value)
      
        len(output).should.equal(3) 
        output[0].should.equal('bitstamp')
        output[1].should.equal('coinbase')
        output[2].should.equal('kraken')

    def test_parse_list_simple_trailing_comma(self):
        value = 'bitstamp,'

        output = configuration.parse_configurable_as_list(value)
      
        len(output).should.equal(1) 
        output[0].should.equal('bitstamp')

    def test_parse_list_more_trailing_comma(self):
        value = 'bitstamp,coinbase,kraken,'

        output = configuration.parse_configurable_as_list(value)
      
        len(output).should.equal(3) 
        output[0].should.equal('bitstamp')
        output[1].should.equal('coinbase')
        output[2].should.equal('kraken')

    def test_parse_list_many_commas(self):
        value = ',bitstamp,coinbase,,,kraken,,,,'

        output = configuration.parse_configurable_as_list(value)
      
        len(output).should.equal(3) 
        output[0].should.equal('bitstamp')
        output[1].should.equal('coinbase')
        output[2].should.equal('kraken')

    def test_configurable_value_money(self):
        value = 'BTC 0.1'

        output = configuration.parse_configurable_value(value)

        output.should.equal(Money('0.1', 'BTC'))

    def test_configurable_value_money_2(self):
        value = 'ETH 0.1'

        output = configuration.parse_configurable_value(value)

        output.should.equal(Money('0.1', 'ETH'))

    def test_configurable_value_bad_money(self):
        value = '1000 USD'

        output = configuration.parse_configurable_value(value)

        output.should.equal('1000 USD')

    def test_configurable_value_number(self):
        value = '133120102'

        output = configuration.parse_configurable_value(value)

        output.should.equal(Decimal('133120102'))

    def test_configurable_value_number_2(self):
        value = '0'

        output = configuration.parse_configurable_value(value)

        output.should.equal(Decimal('0'))

    def test_configurable_value_bool(self):
        value = 'yes'

        output = configuration.parse_configurable_value(value)

        output.should.equal(True)

    def test_configurable_value_bool_2(self):
        value = 'no'

        output = configuration.parse_configurable_value(value)

        output.should.equal(False)

    def test_configurable_value_bool_3(self):
        value = True

        output = configuration.parse_configurable_value(value)

        output.should.equal(True)

    def test_configurable_value_bool_4(self):
        value = False

        output = configuration.parse_configurable_value(value)

        output.should.equal(False)

    def test_configurable_value_string(self):
        value = 'tornado'

        output = configuration.parse_configurable_value(value)

        output.should.equal('tornado')

    def test_parse_sections_trivial(self):
        parser = configuration._get_parser_for_string_config(TRIVIAL_CONFIG_FILE)

        parsed = configuration.parse_sections(parser)

        len(parsed.keys()).should.equal(1)
        parsed.keys().should.equal(['strategy'])
        parsed['strategy'].should.equal({'midpoint': Decimal('0.001')})

    def test_parse_sections_simple(self):
        parser = configuration._get_parser_for_string_config(SIMPLE_CONFIG_FILE)

        parsed = configuration.parse_sections(parser)

        len(parsed.keys()).should.equal(1)
        parsed.keys().should.equal(['strategy'])
        parsed['strategy']['midpoint'].should.equal(Decimal('0.001'))
        parsed['strategy']['quote_depth'].should.equal(Money('20', 'BTC'))
        parsed['strategy']['use_gds'].should.equal(True)
        parsed['strategy']['primary_exchange_name'].should.equal('coinbase_btc_usd')

    def test_parse_sections_multi_section(self):
        parser = configuration._get_parser_for_string_config(MULTISECTION_CONFIG_FILE)

        parsed = configuration.parse_sections(parser)

        len(parsed.keys()).should.equal(2)
        parsed.keys().should.equal(['platform', 'strategy'])
        parsed['strategy']['tick_sleep'].should.equal(Decimal('1'))
        parsed['platform']['audit'].should.equal(False)

    def test_parse_sections_subsection(self):
        parser = configuration._get_parser_for_string_config(SUBSECTION_CONFIG_FILE)

        parsed = configuration.parse_sections(parser)

        len(parsed.keys()).should.equal(2)
        parsed.keys().should.equal(['platform', 'strategy'])
        parsed['strategy']['tick_sleep'].should.equal(Decimal('1'))
        parsed['platform']['audit'].should.equal(False)

        parsed['strategy']['midpoint_weights'].keys().should.equal([
            'coinbase_btc_usd',
            'bitstamp_btc_usd',
        ])

        parsed['strategy']['midpoint_weights']['coinbase_btc_usd']\
            .should.equal(Decimal('0.5'))

        parsed['strategy']['midpoint_weights']['bitstamp_btc_usd']\
            .should.equal(Decimal('0.5'))


