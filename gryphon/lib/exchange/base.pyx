# -*- coding: utf-8 -*-
from collections import defaultdict
import errno
import functools
import inspect
import json
import math
import os
from socket import error as SocketError

from cdecimal import *
from delorean import Delorean, epoch
import termcolor as tc
import requests
from retrying import Retrying
from requests_futures.sessions import FuturesSession

from gryphon.lib.logger import get_logger
from gryphon.lib.models.datum import DatumRecorder
from gryphon.lib.slacker import Slacker
from gryphon.lib.session import get_a_redis_connection
import gryphon.lib.metrics.quote as quote_lib
from gryphon.lib.money import Money
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exceptions import *


logger = get_logger(__name__)

LOG_LINE_LIMIT = 100


class Exchange(object):
    def __init__(self, session=None):
        self.withdrawal_fee = Money('0', 'BTC')
        self.btc_credit_limit = Money('0', 'BTC')
        self.price_decimal_precision = None
        self.volume_decimal_precision = None
        self.volume_currency = 'BTC'

        if session:
            self.session = session
        else:
            self.session = FuturesSession(max_workers=10)
    
    @property
    def redis(self):
        if hasattr(self, '_redis'):
            return self._redis
        else:
            self._redis = get_a_redis_connection()
            return self._redis

    def load_env(self, key):
        return str(os.environ[key])

    ###### Request Methods ######

    def req(self, req_method, url, **kwargs):
        """
        Create a requests-future request.
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

        try:
            response = req.result()
            log_line = response.text

            if len(log_line) > LOG_LINE_LIMIT:
                log_line = log_line[:LOG_LINE_LIMIT]
                log_line += '...'

            logger.debug(u'[%s] API %s - %s' % (
                self.friendly_name,
                api_method,
                log_line,
            ))

            data = response.json(parse_float=Decimal)
        except ValueError: # includes JSONDecodeError
            raise ExchangeAPIFailureException(self, response)
        except (requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError):
            raise ExchangeAPIFailureException(self)
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                raise ExchangeAPIFailureException(self)
            else:
                raise e # Not error we are looking for

        return data

    def from_const(self, mode):
        if mode == Consts.BID:
            return self.bid_string
        elif mode == Consts.ASK:
            return self.ask_string
        else:
            raise ValueError('mode must be a Const')

    def to_const(self, mode):
        if mode == self.bid_string:
            return Consts.BID
        elif mode == self.ask_string:
            return Consts.ASK
        else:
            raise ValueError(
                'mode must be one of %s/%s' % (self.bid_string, self.ask_string),
            )
    
    ###### Helper Methods ######
    
    def send_btc_to_exchange(self, exchange, amount):
        destination_address = exchange.deposit_address()

        logger.info('Sending %s from %s to %s (%s)' % (
            amount,
            self.name,
            exchange.name,
            destination_address,
        ))

        slacker = Slacker('#balancer','balancer', icon_emoji=':zap:')
        slacker.notify('Sending %s from %s to %s (%s)' % (
            amount,
            self.name,
            exchange.name,
            destination_address,
        ))

        result = self.withdraw_bitcoin(destination_address, amount)

        return (
            destination_address,
            result.get('tx'),
            result.get('exchange_withdrawal_id'),
        )

    def cached_orderbook(self, volume_limit=None):
        key = '%s_orderbook' % self.name.lower()
        raw_redis_result = self.redis.get(key)

        try:
            redis_result = json.loads(raw_redis_result)

            orderbook_age = Delorean().epoch - float(redis_result['timestamp'])

            if orderbook_age >= 10:
                raise CachedOrderbookFailure(
                    self,
                    'Cached orderbook more than 10 seconds old',
                )

            # Emerald Havoc sets the timestamp when it gets a new orderbook
            time_fetched = redis_result['timestamp']
            orderbook = redis_result[self.name]

            parsed_orderbook = self.parse_orderbook(
                orderbook,
                volume_limit,
                cached_orders=True,
            )

            parsed_orderbook['time_fetched'] = time_fetched

            return parsed_orderbook
        except CachedOrderbookFailure:
            # let the 'more than 10 seconds old' exception bubble up
            raise
        except Exception as e:
            raise CachedOrderbookFailure(self, 'Unable to parse cached orderbook')

    def cancel_all_open_orders(self):
        [self.cancel_order(o['id']) for o in self.open_orders()]

    def remove_our_orders(self, order_book, open_orders, only_flag=False):
        """
        TODO add flagging back in.
        """
        open_volume_by_price = defaultdict(int)

        for o in open_orders:
            open_volume_by_price[o['price'].amount] += o['volume_remaining']

        for order in order_book['bids'] + order_book['asks']:
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
        order_book['bids'] = [o for o in order_book['bids'] if o.volume > 0]
        order_book['asks'] = [o for o in order_book['asks'] if o.volume > 0]

    def price_quote(self, mode, volume):
        req = self.price_quote_req()
        return self.price_quote_resp(req, mode, volume)

    def price_quote_req(self):
        """
        Returns an expected total cost to buy the given bitcoin volume
        and also the price the bid should be made at.
        """
        return [self.open_orders_req(), self.get_order_book_req()]

    def price_quote_resp(self, reqs, mode, volume):
        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Volume must be %s' % self.volume_currency)

        open_orders = self.open_orders_resp(reqs[0])

        # We need this because liquidity gets removed when we remove our own orders
        # below.
        open_volume = sum([o['volume_remaining'] for o in open_orders])
        order_book = self.get_order_book_resp(reqs[1], volume + open_volume)

        self.remove_our_orders(order_book, open_orders)

        return quote_lib.price_quote_from_orderbook(order_book, mode, volume)

    def create_trade_at_market_price(self, mode, volume):
        price_quote = self.price_quote(mode, volume)

        logger.info(
            u'Quote for %s of %s is %s, place order at %s',
            mode,
            volume,
            price_quote['total_price'],
            price_quote['price_for_order'],
        )

        response = self.create_trade(mode, volume, price_quote['price_for_order'])

        if response.get('success'):
            response['price'] = price_quote['price_for_order']
            return response
        else:
            return None

    def buy_bitcoin(self, volume):
        return self.create_trade_at_market_price(Consts.BID, volume)

    def sell_bitcoin(self, volume):
        return self.create_trade_at_market_price(Consts.ASK, volume)

    def order_details(self, order_id):
        result = self.multi_order_details([order_id])

        if order_id in result:
            return result[order_id]
        else:
            raise ExchangeAPIErrorException(self, 'Order not found')

    def exchange_data(self, db):
        from gryphon.lib.exchange.exchange_factory import make_exchange_data_from_key
        return make_exchange_data_from_key(self.name, db)

    ###### Common Exchange Methods ######

    def auth_request(req_method, url, request_args):
        raise NotImplementedError

    def apply_fee(self, order):
        from gryphon.lib.exchange.exchange_order import Order

        if order.type == Order.ASK:
            order.price += (order.price * self.fee)
        elif order.type == Order.BID:
            order.price -= (order.price * self.fee)

    def balance(self):
        req = self.balance_req()
        return self.balance_resp(req)

    def balance_req(self):
        raise NotImplementedError

    def balance_resp(self, req):
        """
        -> Balance object
        """
        raise NotImplementedError


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

        raw_bids.sort(key = sort_key, reverse=True)
        raw_asks.sort(key = sort_key)

        bids = []
        asks = []

        total_volume = Money(0, self.volume_currency)
        top_bid_price, __ = self.parse_any_order(raw_bids[0], cached_orders)

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

        total_volume = Money(0, self.volume_currency)
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

        return {'bids':bids, 'asks':asks}

    def ticker(self, verify=True):
        req = self.ticker_req(verify=verify)
        return self.ticker_resp(req)

    def ticker_req(self, verify=True):
        raise NotImplementedError

    def ticker_resp(self, req):
        """
        -> {
            high: Money,
            low: Money,
            last: Money,
            volume: Money
        }
        """
        raise NotImplementedError

    def get_order_book(self, volume_limit=None, verify=True):
        req = self.get_order_book_req(verify=verify)
        return self.get_order_book_resp(req, volume_limit)

    def get_order_book_req(self, verify=True):
        if self.use_cached_orderbook:
            return 'CACHED_ORDERBOOK'

        return self._get_order_book_req(verify=verify)

    def get_order_book_resp(self, req, volume_limit=None):
        if req == 'CACHED_ORDERBOOK':
            return self.cached_orderbook(volume_limit)
        else:
            raw_orderbook = self._get_order_book_resp(req)
            fetched_orderbook = self.parse_orderbook(raw_orderbook, volume_limit)
            fetched_orderbook['time_fetched'] = Delorean().epoch

            return fetched_orderbook

    def _get_order_book_req(self, verify=True):
        raise NotImplementedError

    def _get_order_book_resp(self, req):
        """Get the raw orderbook from an exchange"""
        return self.resp(req)

    def _get_raw_bids(self, raw_orderbook):
        """
        The default behaviour in this ant _get_raw_asks works for about 70% of the
        exchanges, the rest override them.
        """
        return raw_orderbook['bids']

    def _get_raw_asks(self, raw_orderbook):
        return raw_orderbook['asks']

    @property
    def _orderbook_sort_key(self):
        return lambda order: float(order[0])

    def parse_order(self, order):
        price = Money(order[0], self.currency)
        volume = Money(order[1], self.volume_currency)

        return (price, volume)

    def create_trade(self, mode, volume, price, is_market_order=False):
        req = self.create_trade_req(mode, volume, price, is_market_order)
        return self.create_trade_resp(req)

    def create_trade_req(self, mode, volume, price, is_market_order=False):
        raise NotImplementedError
        
    def create_trade_resp(self, req):
        """
        -> {success:
            order_id:
            error:?
            }
        """
        raise NotImplementedError

    def open_orders(self):
        req = self.open_orders_req()
        return self.open_orders_resp(req)

    def open_orders_req(self):
        raise NotImplementedError

    def open_orders_resp(self, req):
        """
          -> {
              mode:
              id:
              price:
              volume:
          }
        """
        raise NotImplementedError

    def multi_order_status_req(self):
        return self.open_orders_req()

    def multi_order_status_resp(self, req, order_ids):
        order_ids = [str(o) for o in order_ids]

        open_orders = self.open_orders_resp(req)
        open_order_ids = [o['id'] for o in open_orders]

        orders = {}

        for order_id in order_ids:
            if order_id in open_order_ids:
                orders[order_id] = {'status': 'open'}
            else:
                orders[order_id] = {'status': 'filled'}

        return orders

    def multi_order_details(self, order_ids):
        """
        This is a strange, magical function. We need to handle exchanges where we send
        order_ids in the request [Bitfinex] e.g. 
            r = multi_order_details_req(order_ids)
            multi_order_details_resp(r)
        ...as well as exchanges where we send order_ids in the response (filtering after
        the fact) [Bitstamp]. e.g.
            r = multi_order_details_req()
            multi_order_details_resp(r, order_ids)
        ...and even some strange exchanges where we send it in both the request and the
        response [Kraken].
        """
        try:
            req = self.multi_order_details_req()
        except TypeError: # The method expected parameters which we didn't send
            req = self.multi_order_details_req(order_ids)

        try:
            return self.multi_order_details_resp(req)
        except TypeError: # The method expected parameters which we didn't send
            return self.multi_order_details_resp(req, order_ids)

    def multi_order_details_req(self):
        raise NotImplementedError

    def multi_order_details_resp(self, req, order_ids):
        """
        -> {
            time_created:
            type:
            btc_total:
            fiat_total:
            trades:
        }
        """
        raise NotImplementedError

    def cancel_order(self, order_id):
        req = self.cancel_order_req(order_id)
        return self.cancel_order_resp(req)

    def cancel_order_req(self, order_id):
        raise NotImplementedError

    def cancel_order_resp(self, req):
        """
        -> {success:
            error:
            }
        """
        raise NotImplementedError

    def fiat_deposit_fee(self, deposit_amount):
        return Money(0, self.currency)

    def fiat_withdrawal_fee(self, deposit_amount):
        return Money(0, self.currency)

    def deposit_address(self):
        """
        Override exchange-specific api methods with ENV vars.
        """
        env_key = '%s_DEPOSIT_ADDRESS' % self.name
        return os.environ[env_key]

    def deposit_address_req(self):
        raise NotImplementedError

    def deposit_address_resp(self, req):
        raise NotImplementedError

    def withdraw_bitcoin(self, address, bitcoin_volume):
        req = self.withdraw_bitcoin_req(address, bitcoin_volume)
        return self.withdraw_bitcoin_resp(req)

    def withdraw_bitcoin_req(self, address, bitcoin_volume):
        raise NotImplementedError

    def withdraw_bitcoin_resp(self, req):
        raise NotImplementedError

    def process_db_balance_for_audit(self, db_balance):
        return db_balance

    def pre_audit(self, exchange_data):
        pass

    def audit(self, skip_recent=0):
        raise NotImplementedError

    def maker_taker_fee_difference(self):
        """
        The fee difference between market and limit orders on this exchange.
        Defaults to zero (no difference).
        """
        if self.market_order_fee != None and self.limit_order_fee != None:
            return self.market_order_fee - self.limit_order_fee
        else:
            return Decimal('0')

