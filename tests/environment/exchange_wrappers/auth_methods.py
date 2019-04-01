"""
Test an exchange's authenticated endpoints that don't make any modifying calls.
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import logging
import os
import unittest
import sure
import mock

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money


class ExchangeAuthMethodsTests(object):
    def test_balance(self):
        balance = self.exchange.get_balance()

        assert self.exchange.currency in balance 
        assert self.exchange.volume_currency in balance

    def test_open_orders(self):
        open_orders = self.exchange.get_open_orders()

    def test_recent_trades(self):
        if hasattr(self.exchange, '_get_recent_trades'):
            recent_trades = self.exchange._get_recent_trades()

    def test_get_audit_data(self):
        audit_data = self.exchange.get_order_audit_data()

    def test_price_quote(self):
        quote = self.exchange.get_price_quote(Consts.BID, Money('1', 'BTC'))

    def test_deposit_address(self):
        deposit_address = self.exchange.current_deposit_address
