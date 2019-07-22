"""
https://github.com/binance-jersey/binance-official-api-docs
"""

# -*- coding: utf-8 -*-
import hashlib
import hmac
import time

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

logger = get_logger(__name__)


def binance_signature(params, secret):
    """Signature of a url query string as required by Binance

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


class BinanceJeExchange(ExchangeAPIWrapper):
    currencies = None
    credentials = None
    base_url = "https://api.binance.je"
    endpoints = {
        "ping": {"req_method": "get", "url": "/api/v1/ping"},
        "balance": {"req_method": "get", "url": "/api/v3/account"},
        "prices": {"req_method": "get", "url": "/api/v3/ticker/price"},
        "open_orders": {"req_method": "get", "url": "/api/v3/openOrders"},
    }

    def __init__(self, session=None, configuration=None):
        if self.currencies is None:
            raise NotImplementedError(
                "Cannot instantiate BinanceJeExchange. Use a subclass instead."
            )

        super(BinanceJeExchange, self).__init__(session)
        self.volume_currency = self.currencies["volume"]
        self.currency = self.currencies["base"]
        name_suffix = self.currencies["volume"] + "-" + self.currencies["base"]
        self.name = "BINANCEJE_" + name_suffix
        self.friendly_name = "Binance Jersey " + name_suffix

    def load_credentials(self):
        credentials = ["api_key", "secret"]
        if self.credentials is None:
            self.credentials = {
                credential: self._load_env("BINANCEJE_" + credential.upper())
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
            headers = request_args["headers"]
        except KeyError:
            headers = request_args["headers"] = {}

        headers["X-MBX-APIKEY"] = self.credentials["api_key"]

        try:
            params = request_args["params"]
        except KeyError:
            params = request_args["params"] = {}

        timestamp = int(round(time.time() * 1000))
        params["timestamp"] = timestamp

        signature = binance_signature(params, self.credentials["secret"])
        params["signature"] = signature

        logger.debug("headers: %s" % headers)
        logger.debug("request args: %s" % request_args)

    def ping(self):
        req = self.req(no_auth=True, **self.endpoints["ping"])
        return self.resp(req)

    def get_balance_req(self):
        return self.req(**self.endpoints["balance"])

    def get_balance_resp(self, req):
        response = self.resp(req)
        logger.debug("balance repsonse: %s" % response)

        try:
            balances = {
                currency: Money(balance["free"], currency)
                for balance in response["balances"]
                for currency in Money.CURRENCIES
                if balance["asset"] == currency
            }
            logger.debug("balances: %s" % balances)
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self, "Cannot determine balances from response"
            )

        return Balance(balances)

    def get_prices(self):
        req = self.get_prices_req()
        return self.get_prices_resp(req)

    def get_prices_req(self):
        return self.req(no_auth=True, **self.endpoints["prices"])

    def get_prices_resp(self, req):
        response = self.resp(req)
        return {
            item["symbol"][:3]: Money(item["price"], item["symbol"][-3:])
            for item in response
            if item["symbol"][:3] in Money.CRYPTO_CURRENCIES
        }

    def get_open_orders_req(self):
        return self.req(**self.endpoints["open_orders"])

    def get_open_orders_resp(self, req):
        response = self.resp(req)
        side_to_mode = {"BUY": Consts.BID, "SELL": Consts.ASK}
        return [
            {
                "mode": side_to_mode[order["side"]],
                "id": order["orderId"],
                "price": order["price"],
                "volume_remaining": Money(
                    order["origQty"] - response["executedQty"], self.volume_currency
                ),
            }
            for order in response
        ]


class BinanceJeBTCEURExchange(BinanceJeExchange):
    currencies = {"volume": "BTC", "base": "EUR"}


class BinanceJeBTCGBPExchange(BinanceJeExchange):
    currencies = {"volume": "BTC", "base": "GBP"}


class BinanceJeETHEURExchange(BinanceJeExchange):
    currencies = {"volume": "ETH", "base": "EUR"}


class BinanceJeETHGBPExchange(BinanceJeExchange):
    currencies = {"volume": "ETH", "base": "GBP"}


class BinanceJeLTCEURExchange(BinanceJeExchange):
    currencies = {"volume": "LTC", "base": "EUR"}


class BinanceJeLTCGBPExchange(BinanceJeExchange):
    currencies = {"volume": "LTC", "base": "GBP"}
