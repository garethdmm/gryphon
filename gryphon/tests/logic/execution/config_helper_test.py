"""
Just a few exercises for our configuration library.
"""
import pyximport; pyximport.install()
import unittest
import mock
import sure

from gryphon.execution.lib import config_helper


class TestConfigHelper(unittest.TestCase):
    def test_conf_filenames_builtin_1(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'simple_market_making',
        )

        filename.should.equal('simple_market_making.conf')

    def test_conf_filenames_builtin_2(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'multiexchange_linear',
        )

        filename.should.equal('multiexchange_linear.conf')

    def test_conf_filenames_custom_pyx(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'coinbase_gemini_arb.pyx'
        )

        filename.should.equal('coinbase_gemini_arb.conf')

    def test_conf_filenames_custom_pyx_2(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'active_signal_strat.pyx',
        )

        filename.should.equal('active_signal_strat.conf')

    def test_conf_filenames_custom_py(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'coinbase_gemini_arb.py'
        )

        filename.should.equal('coinbase_gemini_arb.conf')

    def test_conf_filenames_custom_py_2(self):
        filename = config_helper.get_conf_filename_from_strategy_name(
            'active_signal_strat.py',
        )

        filename.should.equal('active_signal_strat.conf')

