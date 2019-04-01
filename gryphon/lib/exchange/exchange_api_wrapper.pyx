"""
ExchangeAPIWrapper base class.

These classes make heavy use of the requests-futures library, which allows us to begin
API requests and then continue execution until we require the result of the request.
This can be a substantial performance increase when doing many requests in a single
thread. To this end most of the endpoints that we support are split into a _req and
_resp function. The first begins the request, and the second blocks on the response.
For each endpoint there is also a function which simply calls both parts in serial. You
can safely use these when performance is not crucial.
"""

from collections import defaultdict
import errno
import functools
import inspect
import json
import os
from socket import error as SocketError

from cdecimal import Decimal
from delorean import Delorean, epoch
import termcolor as tc
import requests
from requests_futures.sessions import FuturesSession

from gryphon.lib.configurable_object import ConfigurableObject
from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.logger import get_logger
from gryphon.lib.metrics import quote as quote_lib
from gryphon.lib.money import Money
from gryphon.lib.session import get_a_redis_connection

logger = get_logger(__name__)


class ExchangeAPIWrapper(ConfigurableObject):
    CACHED_ORDERBOOK = 'CACHED_ORDERBOOK'
    LOG_LINE_LIMIT = 100

    def __init__(self, session=None, configuration=None):
        if session:
            self.session = session
        else:
            self.session = FuturesSession(max_workers=10)

        self.withdrawal_fee = Money('0', 'BTC')
        self.btc_credit_limit = Money('0', 'BTC')
        self.price_decimal_precision = 2
        self.volume_decimal_precision = None
        self.volume_currency = 'BTC'

        # Configurable properties with defaults.
        self.fee = Decimal('0.0005')
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.0001', 'USD')
        self.max_tick_speed = 2
        self.use_cached_orderbook = False

    def configure(self, configuration):
        """
        Initialize fees, balance tolerances, and whether to use cached orderbooks.

        There's an annoying leaking of responsibilities in this function right now.
        It's really the ExchangeCoordinator in gryphon.execution that should know the
        destination for requests, this class should just implement the Exchange API.
        """
        platform_configuration = configuration['platform']
        exchange_configuration = None

        if ('exchanges' in configuration
                and self.name.lower() in configuration['exchanges']):
            exchange_configuration = configuration['exchanges'][self.name.lower()]

        if exchange_configuration is not None and 'emerald' in exchange_configuration:
            # Exchange-specific configuraton overrides the platform's use of emerald
            # or not.
            self.use_cached_orderbook = exchange_configuration['emerald']
        elif 'emerald' in platform_configuration:
            self.use_cached_orderbook = platform_configuration['emerald']

        if not exchange_configuration:
            return

        self.init_configurable('market_order_fee', exchange_configuration)
        self.init_configurable('limit_order_fee', exchange_configuration)
        self.init_configurable('fiat_balance_tolerance', exchange_configuration)
        self.init_configurable('volume_balance_tolerance', exchange_configuration)
        self.init_configurable('max_tick_speed', exchange_configuration)
        self.init_configurable('min_order_size', exchange_configuration)

    def place_order(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER):
        """
        Place an order on the exchange.
        """
        req = self.place_order_req(mode, volume, price, order_type)
        return self.place_order_resp(req)
 
    def place_order_req(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER):
        raise NotImplementedError

    def place_order_resp(self, req):
        raise NotImplementedError

    def market_order(self, mode, volume):
        """
        Place a market order on the exchange.
        """
        return self.place_order(mode, volume, order_type=order_types.MARKET_ORDER)
    
    def market_order_req(self, mode, volume):
        raise NotImplementedError

    def market_order_resp(self, req):
        raise NotImplementedError

    def limit_order(self, mode, volume, price):
        """
        Place a limit order on the exchange.
        """
        return self.place_order(mode, volume, price)

    def limit_order_req(self, mode, volume, price):
        raise NotImplementedError

    def limit_order_resp(self, req):
        raise NotImplementedError

    def get_open_orders(self):
        req = self.get_open_orders_req()
        return self.get_open_orders_resp(req)

    def get_open_orders_req(self):
        raise NotImplementedError

    def get_open_orders_resp(self, req):
        raise NotImplementedError

    def cancel_order(self, order_id):
        """
        Cancel an open order.
        """
        req = self.cancel_order_req(order_id)
        return self.cancel_order_resp(req)

    def cancel_order_req(self, order_id):
        raise NotImplementedError

    def cancel_order_resp(self, req):
        raise NotImplementedError

    def cancel_all_open_orders(self):
        """
        Cancel all open orders. Some exchanges provide a special endpoint for this, in
        which case the subclass should override this function.
        """
        for order in self.get_open_orders():
            self.cancel_order(order['id'])

    def get_order_details(self, order_id):
        """
        Get all the relevant information about any order, open or close. Exchanges have
        divergent behaviour on this action, some don't give any information about
        cancelled orders, some keep records on cancelled orders for a limited time, and
        some keep records forever.
        """
        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req)

    def get_order_details_req(self, order_id):
        raise NotImplementedError

    def get_order_details_resp(self, req):
        raise NotImplementedError

    def get_multi_order_details(self, order_ids):
        """
        Get information for several orders at once. Some exchanges provide an endpoint
        that gives information about multiple orders at once, and this is way quicker
        than doing independent requests for each order.
        """
        req = self.get_multi_order_details_req(order_ids)
        return self.get_multi_order_details_resp(req)

    def get_multi_order_details_req(self, order_ids):
        raise NotImplementedError

    def get_multi_order_details_resp(self, req):
        raise NotImplementedError
   
    def get_balance(self):
        """
        Get our account balance on the exchange.
        """
        req = self.get_balance_req()
        return self.get_balance_resp(req)
 
    def get_balance_req(self):
        raise NotImplementedError

    def get_balance_resp(self, req):
        raise NotImplementedError

    def withdraw(self):
        """
        Withdraw part of our balance from this exchange.
        """
        pass

    def withdraw_req(self):
        raise NotImplementedError

    def withdraw_resp(self, req):
        raise NotImplementedError

    def get_order_audit_data(self):
        """
        This function gets a list of recent orders on our account mapped to the amount
        of that order that was filled. This function is used heavily in auditing.
        """
        raise NotImplementedError

    def get_ticker(self, verify=True):
        """
        Get the current ticker, which usually has a summary of recent activity on the
        market.
        """
        req = self.get_ticker_req(verify=verify)
        return self.get_ticker_resp(req)

    def get_ticker_req(self, verify=True):
        raise NotImplementedError

    def get_ticker_resp(self, req):
        raise NotImplementedError

    def get_orderbook(self, volume_limit=None, verify=True):
        """
        Get the current orderbook.
        """
        req = self.get_orderbook_req(verify)
        return self.get_orderbook_resp(req, volume_limit)

    def get_orderbook_req(self, verify=True):
        if self.use_cached_orderbook:
            return ExchangeAPIWrapper.CACHED_ORDERBOOK

        return self._get_orderbook_from_api_req(verify=verify)

    def get_orderbook_resp(self, req, volume_limit=None):
        if req == ExchangeAPIWrapper.CACHED_ORDERBOOK:
            return self._get_orderbook_from_cache(volume_limit)
        else:
            raw_orderbook = self._get_orderbook_from_api_resp(req)

            parsed_orderbook = self.parse_orderbook(raw_orderbook, volume_limit)
            parsed_orderbook['time_parsed'] = Delorean().epoch

            return parsed_orderbook

    def get_price_quote(self, mode, volume):
        """
        Returns an expected total cost to fill a given order, as well as the price the
        order should be entered at to clear the desired volume if it is a limit order.
        """
        req = self.get_price_quote_req()
        return self.get_price_quote_resp(req, mode, volume)

    def get_price_quote_req(self):
        return [self.get_open_orders_req(), self.get_orderbook_req()]

    def get_price_quote_resp(self, reqs, mode, volume):
        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Volume must be %s' % self.volume_currency)

        open_orders = self.get_open_orders_resp(reqs[0])

        # We need to ignore orders we currently have on the books as most exchanges
        # don't allow self-trading.
        open_volume = sum([o['volume_remaining'] for o in open_orders])
        orderbook = self.get_orderbook_resp(reqs[1], volume + open_volume)

        orderbook = self.remove_orders_from_orderbook(orderbook, open_orders)

        return quote_lib.price_quote_from_orderbook(orderbook, mode, volume)

    def remove_orders_from_orderbook(self, orderbook, open_orders, only_flag=False):
        """
        Remove our own orders from an orderbook.
        """
        open_volume_by_price = defaultdict(int)

        for o in open_orders:
            open_volume_by_price[o['price'].amount] += o['volume_remaining']

        for order in orderbook['bids'] + orderbook['asks']:
            open_volume = open_volume_by_price.get(
                order.price.amount, Money('0', 'BTC'),
            )

            if open_volume > 0:
                volume_to_remove = min(open_volume, order.volume)

                if only_flag:
                    order.status = Order.FLAGGED
                else:
                    order.volume -= volume_to_remove

                open_volume -= volume_to_remove

        # Remove 0-volume orders.
        orderbook['bids'] = [o for o in orderbook['bids'] if o.volume > 0]
        orderbook['asks'] = [o for o in orderbook['asks'] if o.volume > 0]

        return orderbook

    @property
    def _orderbook_sort_key(self):
        return lambda order: float(order[0])

    def parse_order(self, order):
        price = Money(order[0], self.currency)
        volume = Money(order[1], self.volume_currency)

        return price, volume

    def parse_cached_order(self, order):
        price = Money(order[0], self.currency)
        volume = Money(order[1], self.volume_currency)
        return (price, volume)

    def parse_any_order(self, order, is_cached_order=False):
        if is_cached_order:
            price, volume = self.parse_cached_order(order)
        else:
            price, volume = self.parse_order(order)

        return price, volume

    def parse_orderbook(self, raw_orderbook, volume_limit=None, price_limit=None, cached_orders=False):
        """
        Returns a dictionary containing a sorted list of asks and a sorted list of bids.
        """

        if cached_orders:
            raw_bids = raw_orderbook['bids']
            raw_asks = raw_orderbook['asks']
            sort_key = lambda o: float(o[0])
        else:
            raw_bids = self._get_raw_bids(raw_orderbook)
            raw_asks = self._get_raw_asks(raw_orderbook)
            sort_key = self._orderbook_sort_key

        raw_bids.sort(key=sort_key, reverse=True)
        raw_asks.sort(key=sort_key)

        bids = []
        asks = []

        total_volume = Money(0, self.volume_currency)
        top_bid_price, _ = self.parse_any_order(raw_bids[0], cached_orders)

        for bid in raw_bids:
            bid_price, bid_volume = self.parse_any_order(bid, cached_orders)

            if price_limit:
                bid_threshold = top_bid_price - price_limit

                if bid_price < bid_threshold:
                    break

            bids.append(Order(bid_price, bid_volume, self, Order.BID))

            total_volume += bid_volume

            if volume_limit and total_volume > volume_limit:
                break

        total_volume = Money('0', self.volume_currency)
        top_ask_price, __ = self.parse_any_order(raw_asks[0], cached_orders)

        for ask in raw_asks:
            ask_price, ask_volume = self.parse_any_order(ask, cached_orders)

            if price_limit:
                ask_threshold = top_ask_price + price_limit

                if ask_price > ask_threshold:
                    break

            asks.append(Order(ask_price, ask_volume, self, Order.ASK))

            total_volume += ask_volume

            if volume_limit and total_volume > volume_limit:
                break

        return {'bids': bids, 'asks': asks}


    # Request methods. All requests to exchange APIs are filtered through these
    # functions which make heavy use of the request-futures library to minimize
    # blocking on Exchange API calls.

    def req(self, req_method, url, **kwargs):
        """
        Place a request to the exchange api and return us a request-future object so
        that our code-path can continue execution until we need the result of the
        request.
      
        This function handles the interface with the request-futures library as well as
        dispatches to the auth_request method if we're making an authenticated call like
        to place an order or get our balance.
        """

        # If the exchange has a base_url set for it's API we can send in only the
        # path to the API endpoint we're trying to reach.
        if url[:4] != 'http':
            url = self.base_url + url

        try:
            no_auth = kwargs['no_auth']
            del kwargs['no_auth']
        except KeyError:
            no_auth = False

        if not no_auth:
            self.auth_request(req_method, url, kwargs)

        req_method = req_method.lower()

        if req_method == 'post':
            future = self.session.post(url, **kwargs)
        elif req_method == 'get':
            future = self.session.get(url, **kwargs)
        elif req_method == 'delete':
            future = self.session.delete(url, **kwargs)
        else:
            raise ValueError('%s method not supported' % req_method)

        return future

    def resp(self, req):
        """
        Get the response from a requests-futures object.
        """

        # Get the function name that called us.
        try:
            stack = inspect.stack()
            api_method = stack[1][3]

            if api_method == 'resp':
                api_method = stack[2][3]

            api_method = api_method.replace('_resp', '')
        except IndexError:
            api_method = 'unknown'

        response = None

        try:
            response = req.result()
            log_line = response.text

            if len(log_line) > ExchangeAPIWrapper.LOG_LINE_LIMIT:
                log_line = log_line[: ExchangeAPIWrapper.LOG_LINE_LIMIT]
                log_line += '...'

            logger.debug(u'[%s] API %s - %s' % (
                self.friendly_name,
                api_method,
                log_line,
            ))

            data = response.json(parse_float=Decimal)
        except ValueError:  # This includes JSONDecodeError.
            raise exceptions.ExchangeAPIFailureException(self, response)
        except (requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError):
            raise exceptions.ExchangeAPIFailureException(self)
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                raise exceptions.ExchangeAPIFailureException(self)
            else:
                raise e

        return data

    def auth_request(req_method, url, request_args):
        """
        This function handles all calls to authenticated endpoints in the exchange API,
        e.g. getting balances or placing orders, in contrast to public methods like
        getting the current orderbook.
        """
        raise NotImplementedError

    # Helper functions and private methods.

    def _get_orderbook_from_api_req(self, verify=True):
        """
        Get the current raw (unparsed) orderbook directly from the exchange API.
        """
        raise NotImplementedError

    def _get_orderbook_from_api_resp(self, req):
        return self.resp(req)

    def _get_raw_bids(self, raw_orderbook):
        """
        This function parses the bids out of the raw orderbook. This is a sane default
        function that works for most exchanges, the rest need to overload this function
        in their implementation.
        """
        return raw_orderbook['bids']

    def _get_raw_asks(self, raw_orderbook):
        """
        Sibling to _get_raw_bids.
        """
        return raw_orderbook['asks']

    def _get_orderbook_from_cache(self, volume_limit=None):
        """
        Get the current orderbook for the exchange from our local cache.
        """

        key = '%s_orderbook' % self.name.lower()
        raw_redis_result = self.redis.get(key)

        try:
            redis_result = json.loads(raw_redis_result)

            orderbook_age = Delorean().epoch - float(redis_result['timestamp'])

            if orderbook_age >= 10:
                raise exceptions.CachedOrderbookFailure(
                    self,
                    'Cached orderbook more than 10 seconds old',
                )

            time_fetched = redis_result['timestamp']
            orderbook = redis_result[self.name]

            parsed_orderbook = self.parse_orderbook(
                orderbook,
                volume_limit,
                cached_orders=True,
            )

            parsed_orderbook['time_fetched'] = time_fetched

            return parsed_orderbook
        except exceptions.CachedOrderbookFailure:
            raise
        except Exception as e:
            raise exceptions.CachedOrderbookFailure(
                self,
                'Unable to parse cached orderbook',
            )

    def _load_env(self, key):
        return str(os.environ[key])

    def _order_mode_from_const(self, mode):
        if mode == Consts.BID:
            return self.bid_string
        elif mode == Consts.ASK:
            return self.ask_string
        else:
            raise ValueError('mode must be a Const')

    def _order_mode_to_const(self, mode):
        if mode == self.bid_string:
            return Consts.BID
        elif mode == self.ask_string:
            return Consts.ASK
        else:
            raise ValueError(
                'mode must be one of %s/%s' % (self.bid_string, self.ask_string),
            )

    @property
    def redis(self):
        if hasattr(self, '_redis'):
            return self._redis
        else:
            self._redis = get_a_redis_connection()
            return self._redis

    def maker_taker_fee_difference(self):
        """
        Simple helper function to give the fee difference between market and limit
        orders on this exchange. Defaults to zero (no difference).
        """
        if self.market_order_fee != None and self.limit_order_fee != None:
            return self.market_order_fee - self.limit_order_fee
        else:
            return Decimal('0')

    def exchange_account_db_object(self, db):
        """
        Just a helper function to get our database representation of the current
        account.
        """
        return exchange_factory.make_exchange_data_from_key(self.name, db)

    def process_db_balance_for_audit(self, db_balance):
        """
        Exchange trading engines have different characteristics when it comes to
        decimal precision and rounding behaviour. This function massages our database
        record of our balance on this exchange so that it can be compared to the
        exchange API's output.
        """
        return db_balance

    def pre_audit(self, exchange_data):
        """
        Some exchanges have extra actions that need to be taken before an audit.
        """
        pass

    def fiat_deposit_fee(self, deposit_amount):
        return Money('0', self.currency)

    def fiat_withdrawal_fee(self, deposit_amount):
        return Money('0', self.currency)

    @property
    def current_deposit_address(self):
        deposit_address_env_key = '%s_DEPOSIT_ADDRESS' % self.name
        return self._load_env(deposit_address_env_key)

    def get_new_deposit_address(self):
        """
        TODO: This method is unimplemented everywhere, but some exchanges do supply this
        functionality in their API, so it would be a good thing add in the future.
        """
        raise NotImplementedError

    def deposit_address_req(self):
        raise NotImplementedError

    def deposit_address_resp(self, req):
        raise NotImplementedError

    def withdraw_crypto(self, address, volume):
        """
        Withdraw a cryptocurrency amount to an external address.
        """
        req = self.withdraw_crypto_req(address, volume)
        return self.withdraw_crypto_resp(req)

    def withdraw_crypto_req(self, address, volume):
        raise NotImplementedError

    def withdraw_crypto_resp(self, req):
        raise NotImplementedError

