from __future__ import absolute_import

import gryphon.lib; gryphon.lib.monkeypatch_decimal_to_cdecimal()

from gryphon.lib.forex import USDCurrencyConverter

import json
import decimal
# need absolute_import from above so that this doesn't load our current file
import money as super_money


class Money(super_money.Money):
    FIAT_CURRENCIES = ["USD", "CAD", "EUR"]
    CRYPTO_CURRENCIES = ["BTC", "ETH", "BCH"]
    CURRENCIES = FIAT_CURRENCIES + CRYPTO_CURRENCIES

    def __init__(self, amount="0", currency=None):
        if isinstance(amount, basestring):
            amount = amount.replace(",", "")

        try:
            self.amount = decimal.Decimal(amount)
        except decimal.InvalidOperation:
            raise ValueError(
                "amount value could not be converted to Decimal(): '{}'".format(amount),
            )

        if currency not in self.CURRENCIES:
            raise ValueError("invalid currency value: '{}'".format(currency))

        self.currency = currency

    def round_to_decimal_places(self, places, rounding=decimal.ROUND_UP):
        """
        Round a money object to n decimal places.

        Useful for truncating BTC amounts before sending them to exchange APIs
        Default rounds up (??? not sure why)
        but you can pass in your own rounding setting
        """
        bucket = decimal.Decimal(10) ** -places
        return self.round_to_bucket(bucket, rounding=rounding)

    def round_to_bucket(self, bucket, rounding=decimal.ROUND_DOWN):
        """
        Round a money object to the nearest bucket.

        Useful for getting friendly wire/btc amounts (eg: 1,223.45 => 1,000.00)
        Default rounds down, but you can pass in your own rounding setting
        """
        rounded_amount = (self.amount / bucket).to_integral_value(rounding=rounding) * bucket
        return self.__class__(rounded_amount, self.currency)

    def __repr__(self):
        amount = self.amount
        # fix case of 0E-8
        if amount == 0:
            amount = 0
        return "{} {}".format(self.currency, amount)

    def __unicode__(self):
        if self.currency == 'BTC':
            return u"{} {:,.8f}".format(self.currency, self.amount)
        else:
            return u"{} {:,.2f}".format(self.currency, self.amount)

    def to_json(self):
        return repr(self)

    def to(self, currency, date=None, exchange_rate_to_usd=None):
        """Return equivalent money object in another currency from a specific date"""
        if currency == self.currency:
            return self

        if exchange_rate_to_usd:
            if not isinstance(exchange_rate_to_usd, decimal.Decimal):
                raise ValueError("exchange_rate_to_usd must be a Decimal")
            if exchange_rate_to_usd <= 0:
                raise ValueError("exchange_rate_to_usd must be a positive number")
            if currency != "USD":
                raise ValueError("Must be converting to USD to use exchange_rate_to_usd")
            usd_amount = self.amount * exchange_rate_to_usd
            return self.__class__(usd_amount, "USD")

        if date:
            a = USDCurrencyConverter.historical_rate(self.currency, date)
            b = USDCurrencyConverter.historical_rate(currency, date)
        else:
            a = USDCurrencyConverter.rate(self.currency)
            b = USDCurrencyConverter.rate(currency)
        rate = b / a
        amount = self.amount * rate
        return self.__class__(amount, currency)
