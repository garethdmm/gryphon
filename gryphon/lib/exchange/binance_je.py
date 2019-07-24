# -*- coding: utf-8 -*-
"""
https://github.com/binance-jersey/binance-official-api-docs
"""

import hashlib
import hmac
import time

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money


class BinanceJeExchange(ExchangeAPIWrapper):
    """A base class to implement support for the Binance Jersey Exchange.

    This class is a pseudo-abstract class. It is not intended to be
    instantiated itself and does not appear as a supported exchange in
    gryphon.lib.exchange.exchange_factory.

    Instead, there are subclasses of this class for each currency pair that
    the exchange supports.

    Class Attributes
    ----------------
    currencies : dict
        Set to None in this class but must be defined in any subclass with
        keys 'volume' and 'base' mapping to valid currencies in gryphon.lib.money

        This dict is used in the constructor method to set the instance
        attributes 'volume_currency' and 'currency' as required by the
        framework

    base_url : str
        The base url for the Binance Jersey API

    endpoints : dict
        Mapping an endpoint name to the relevant 'req_method' and 'url'
        parameters suitable for passing to a request object constructor.
    """
    currencies = None
    base_url = 'https://api.binance.je'
    endpoints = {
        'ping': {'req_method': 'get', 'url': '/api/v1/ping'},
        'balance': {'req_method': 'get', 'url': '/api/v3/account'},
        'ticker': {'req_method': 'get', 'url': '/api/v1/ticker/24hr'},
        'open_orders': {'req_method': 'get', 'url': '/api/v3/openOrders'},
        'orderbook': {'req_method': 'get', 'url': '/api/v1/depth'},
    }

    @staticmethod
    def signature(params, secret):
        """Signature of a url query string as required by Binance Jersey.

        Parameters
        ----------
        params : dict
            query string parameters from a url as given by a request object
        secret : str
            binance user secret for signing the query string

        Returns
        -------
        str
        """
        query_string = ""

        for key in sorted(params.keys()):
            query_string += key + "=" + str(params[key]) + "&"
        query_string = query_string[:-1]

        return hmac.new(secret, query_string, hashlib.sha256).hexdigest()

    def __init__(self, session=None, configuration=None):
        if self.currencies is None:
            raise NotImplementedError(
                'Cannot instantiate BinanceJeExchange. Use a subclass instead.',
            )

        super(BinanceJeExchange, self).__init__(session)
        self.credentials = None
        self.volume_currency = self.currencies['volume']
        self.currency = self.currencies['base']
        self.symbol = self.currencies['volume'] + self.currencies['base']
        name_suffix = self.currencies['volume'] + '-' + self.currencies['base']
        self.name = 'BINANCEJE_' + name_suffix
        self.friendly_name = 'Binance Jersey ' + name_suffix

    def load_credentials(self):
        credentials = ['api_key', 'secret']
        if self.credentials is None:
            self.credentials = {
                credential: self._load_env('BINANCEJE_' + credential.upper())
                for credential in credentials
            }

    def auth_request(self, req_method, url, request_args):
        """Modify a request to add authentication header and query string.

        Overrides the not implemented method from the base class.

        For authenticated endpoints, Binance requires the api key in the
        request header and a timestamp and signature within the query string.
        """
        self.load_credentials()

        try:
            headers = request_args['headers']
        except KeyError:
            headers = request_args['headers'] = {}

        headers['X-MBX-APIKEY'] = self.credentials['api_key']

        try:
            params = request_args['params']
        except KeyError:
            params = request_args['params'] = {}

        timestamp = int(round(time.time() * 1000))
        params['timestamp'] = timestamp
        params['signature'] = self.signature(params, self.credentials['secret'])

    def ping(self):
        req = self.req(no_auth=True, **self.endpoints['ping'])
        return self.resp(req)

    def get_balance_req(self):
        return self.req(**self.endpoints['balance'])

    def get_balance_resp(self, req):
        response = self.resp(req)

        try:
            balances = {
                currency: Money(balance['free'], currency)
                for balance in response['balances']
                for currency in Money.CURRENCIES
                if balance['asset'] == currency
            }
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self, 'Cannot determine balances from response'
            )

        return Balance(balances)

    def get_ticker_req(self, verify=True):
        return self.req(
            no_auth=True,
            verify=verify,
            params={'symbol': self.symbol},
            **self.endpoints['ticker']
        )

    def get_ticker_resp(self, req):
        response = self.resp(req)
        return {
            'high': Money(response['highPrice'], self.currency),
            'low': Money(response['lowPrice'], self.currency),
            'last': Money(response['lastPrice'], self.currency),
            'volume': Money(response['volume'], self.volume_currency),
        }

    def get_open_orders_req(self):
        return self.req(**self.endpoints['open_orders'])

    def get_open_orders_resp(self, req):
        response = self.resp(req)
        side_to_mode = {'BUY': Consts.BID, 'SELL': Consts.ASK}
        return [
            {
                'mode': side_to_mode[order['side']],
                'id': order['orderId'],
                'price': order['price'],
                'volume_remaining': Money(
                    order['origQty'] - response['executedQty'], self.volume_currency
                ),
            }
            for order in response
        ]

    def _get_orderbook_from_api_req(self, verify=True):
        return self.req(
            no_auth=True,
            verify=verify,
            params={'symbol': self.symbol},
            **self.endpoints['orderbook']
        )

    def _get_orderbook_from_api_resp(self, req):
        return self.resp(req)

class BinanceJeBTCEURExchange(BinanceJeExchange):
    currencies = {'volume': 'BTC', 'base': 'EUR'}


class BinanceJeBTCGBPExchange(BinanceJeExchange):
    currencies = {'volume': 'BTC', 'base': 'GBP'}


class BinanceJeETHEURExchange(BinanceJeExchange):
    currencies = {'volume': 'ETH', 'base': 'EUR'}


class BinanceJeETHGBPExchange(BinanceJeExchange):
    currencies = {'volume': 'ETH', 'base': 'GBP'}


class BinanceJeLTCEURExchange(BinanceJeExchange):
    currencies = {'volume': 'LTC', 'base': 'EUR'}


class BinanceJeLTCGBPExchange(BinanceJeExchange):
    currencies = {'volume': 'LTC', 'base': 'GBP'}
