"""
Exchange documentation: https://docs.gemini.com/rest-api/
"""
# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import decimal
import hashlib
import hmac
import json
import time

from cdecimal import *

from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class GeminiBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(GeminiBTCUSDExchange, self).__init__(session)

        self.name = u'GEMINI_BTC_USD'
        self.friendly_name = u'Gemini BTC-USD'
        self.base_url = 'https://api.gemini.com/v1'
        self.currency = 'USD'
        self.volume_currency = 'BTC'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        self.gemini_pair_symbol = 'btcusd'

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.0025')  # Updated by Gareth on 2016-9-20.
        self.limit_order_fee = Decimal('0.0000')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.00001', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def get_ticker_req(self, verify=True):
        """
        Gemini has a ticker but it doesn't conform to our expected outputs. TODO decide
        what to do here.
        """
        pass

    def get_ticker_resp(self, req):
        return {
            'high': None,
            'low': None,
            'last': None,
            'volume': None,
        }

    def get_balance_req(self):
        return self.req('post', '/balances')

    def get_balance_resp(self, req):
        raw_balances = self.resp(req)

        btc_available = None
        usd_available = None

        for raw_balance in raw_balances:
            if raw_balance['currency'] == self.volume_currency:
                volume_currency_available = Money(
                    raw_balance['available'],
                    self.volume_currency,
                )
            elif raw_balance['currency'] == self.currency:
                price_currency_available = Money(
                    raw_balance['available'],
                    self.currency,
                )

        if volume_currency_available == None or price_currency_available == None:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'missing expected balances',
            )

        balance = Balance()
        balance[self.volume_currency] = volume_currency_available
        balance[self.currency] = price_currency_available

        return balance

    def _get_orderbook_from_api_req(self, verify=True):
        return self.req(
            'get',
            '/book/%s?limit_bids=0&limit_asks=0' % self.gemini_pair_symbol,
            no_auth=True,
            verify=verify,
        )

    @property
    def _orderbook_sort_key(self):
        return lambda o: float(o['price'])

    def parse_order(self, order):
        price = Money(order['price'], self.currency)
        volume = Money(order['amount'], self.volume_currency)

        return price, volume

    # Below this line is not good.

    def all_trades(self, until=None):
        req = self.all_trades_req(until)
        return self.all_trades_resp(req)

    def all_trades_req(self, until=None):
        payload = {
            'symbol': self.gemini_pair_symbol,
            'limit_trades': 500,
        }

        if until:
            payload['until'] = str(until)

        return self.req('post', '/mytrades', data=payload)

    def all_trades_resp(self, req):
        return self.resp(req)

    def trades_for_orders(self, order_ids):
        req = self.trades_for_orders_req()
        return self.trades_for_orders_resp(req, order_ids)

    def trades_for_orders_req(self):
        return self.all_trades_req()

    def trades_for_orders_resp(self, req, order_ids):
        order_ids = [unicode(o) for o in order_ids]
        trades = self.all_trades_resp(req)

        matching_trades = {}

        for trade in trades:
            oid = unicode(trade['order_id'])

            if oid in order_ids:
                if not oid in matching_trades:
                    matching_trades[oid] = []

                matching_trades[oid].append(trade)

        return matching_trades

    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        side = self._order_mode_from_const(mode)

        if price.currency not in ['USD', 'BTC']:
            raise ValueError('Invalid price currency %s' % price.currency)
        if volume.currency not in ['BTC', 'ETH']:
            raise ValueError('Invalid volume currency %s' % volume.currency)

        # TODO should this be rounding based on BID/ASK instead of always truncating?
        price_str = '%.2f' % price.amount
        volume_str = '%.8f' % volume.amount

        payload = {
            'symbol': self.gemini_pair_symbol,
            'amount': volume_str,
            'price': price_str,
            'side': side,
            'type': 'exchange limit',
        }

        return self.req('post', '/order/new', data=payload)

    def place_order_resp(self, req):
        response = self.resp(req)

        try:
            order_id = str(response['order_id'])

            return {'success': True, 'order_id': order_id}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self, 
                'response does not contain an order id',
            )

    def get_open_orders_req(self):
        return self.req('post', '/orders')

    def get_open_orders_resp(self, req):
        raw_open_orders = self.resp(req)
        open_orders = []

        for raw_order in raw_open_orders:
            # Skip open orders on other pairs.
            if raw_order['symbol'] != self.gemini_pair_symbol:
                continue

            mode = self._order_mode_to_const(raw_order['side'])
            volume = Money(raw_order['original_amount'], self.volume_currency)

            volume_remaining = Money(
                raw_order['remaining_amount'],
                self.volume_currency,
            )

            order = {
                'mode': mode,
                'id': str(raw_order['id']),
                'price': Money(raw_order['price'], self.currency),
                'volume': volume,
                'volume_remaining': volume_remaining
            }

            open_orders.append(order)

        return open_orders

    def get_order_details(self, order_id):
        """
        Our implementation of the order_details functions is a little hacky, so we have
        to overload this function from the base class to make this function work.
        """
        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req, order_id)

    def get_order_details_req(self, order_id):
        return self.get_multi_order_details_req()

    def get_order_details_resp(self, req, order_id):
        return self.get_multi_order_details_resp(req, [order_id])[order_id]

    def get_multi_order_details(self, order_id):
        """
        Same hack here as in get_order_details.
        """
        req = self.get_multi_order_details_req()
        return self.get_multi_order_details_resp(req, order_id)

    def get_multi_order_details_req(self):
        return self.trades_for_orders_req()

    def get_multi_order_details_resp(self, req, order_ids):
        order_ids = [unicode(o) for o in order_ids]

        multi_trades = self.trades_for_orders_resp(req, order_ids)
        data = {}

        for order_id in order_ids:
            total_price_currency = Money('0', self.currency)
            total_volume = Money('0', self.volume_currency)
            our_trades = []
            our_type = None

            if order_id in multi_trades:
                trades = multi_trades[order_id]

                for t in trades:
                    volume_amount = Money(t['amount'], self.volume_currency)
                    fee = Money(t['fee_amount'], t['fee_currency'])
                    price = Money(t['price'], self.currency)
                    price_currency_amount = price * volume_amount.amount
                    our_type = self._order_mode_to_const(t['type'].lower())

                    total_price_currency += price_currency_amount
                    total_volume += volume_amount

                    our_trades.append({
                        'time': int(float(t['timestamp'])),
                        'trade_id': unicode(t['tid']),
                        'fee': fee,
                        self.volume_currency.lower(): volume_amount,
                        'fiat': price_currency_amount,
                    })

            try:
                time_created = min([t['time'] for t in our_trades])
            except ValueError: # no trades
                time_created = None

            data[order_id] = {
                'time_created': time_created,
                'type': our_type,
                '%s_total' % self.volume_currency.lower(): total_volume,
                'fiat_total': total_price_currency,
                'trades': our_trades
            }

        return data

    def cancel_all_open_orders(self):
        """
        Gemini has it's own cancel-all-orders endpoint that doesn't require us to
        iterate through the list of open orders, so we override this.
        """
        req = self.cancel_all_open_orders_req()
        return self.cancel_all_open_orders_resp(req)

    def cancel_all_open_orders_req(self):
        return self.req('post', '/order/cancel/all')

    def cancel_all_open_orders_resp(self, req):
        resp = self.resp(req)

        if resp['result'] == 'ok':
            return {'success': True}
        else:
            return {'success': False}

    def cancel_order_req(self, order_id):
        payload = {
            'order_id': order_id,
        }

        return self.req('post', '/order/cancel', data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)

        return {'success': True}

    def process_db_balance_for_audit(self, db_balance):
        # Gemini truncates BTC to 8 decimal places, but stores it to 10
        # and USD truncates to 2 decimal places, but is stored as 14
        if db_balance.currency == self.volume_currency:
            db_balance = db_balance.round_to_decimal_places(8, decimal.ROUND_FLOOR)
        elif db_balance.currency == self.currency:
            db_balance = db_balance.round_to_decimal_places(2, decimal.ROUND_FLOOR)

        return db_balance

    def get_order_audit_data(self, skip_recent=0):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (including
        only orders that have some trades).
        """
        orders = OrderedDict()
        trades_to_audit = self.all_trades()

        # Trades from the same order aren't guaranteed to be next to each other, so we
        # need to group them.
        trades_to_audit.sort(key=lambda t: (t['order_id'], t['timestamp']), reverse=True)

        # We want to skip recent orders, but splitting between trades will give us
        # incorrect volume_filled.
        orders_to_skip = skip_recent

        while orders_to_skip > 0:
            try:
                trade = trades_to_audit.pop(0)

                # We found a boundary.
                if trade['order_id'] != trades_to_audit[0]['order_id']:
                    orders_to_skip -= 1
            except IndexError:
                # If we run off the end of the list, we are trying to strip all trades.
                trades_to_audit = []
                orders_to_skip = 0

        for trade in trades_to_audit:
            order_id = str(trade['order_id'])

            try:
                orders[order_id] += abs(Money(trade['amount'], self.volume_currency))
            except KeyError:
                orders[order_id] = abs(Money(trade['amount'], self.volume_currency))

        # Remove the oldest 2 orders, because its trades might be wrapped around a page
        # gap. This would give us an innacurate volume_filled number.
        # We need to remove 2, since there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        return Money('10', 'USD')

    # Request methods.

    def req(self, req_method, url, **kwargs):
        req = super(GeminiBTCUSDExchange, self).req(req_method, url, **kwargs)
        return req

    def resp(self, req):
        response = super(GeminiBTCUSDExchange, self).resp(req)

        if 'message' in response:
            errors_string = str(response['message'])

            if 'InsufficientFunds' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Order' in errors_string and 'not found' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'InvalidNonce' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        return response

    def auth_request(self, req_method, url, request_args):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('GEMINI_BTC_USD_API_KEY')
            self.secret = self._load_env('GEMINI_BTC_USD_API_SECRET')

        endpoint = url.replace(self.base_url, '')
        endpoint = '/v1' + endpoint

        timestamp = int(round(time.time() * 1000))
        nonce = timestamp * 1000 + 1000000000

        try:
            data = request_args['data']
            # The payload get passed as a header, so we don't want to POST them.
            request_args['data'] = {}
        except KeyError:
            data = {}

        payload_object = {
            'request': endpoint,
            'nonce': str(nonce),
        }

        payload_object.update(data)
        payload_json = json.dumps(payload_object)
        payload = str(base64.b64encode(payload_json))

        sig = hmac.new(self.secret, payload, hashlib.sha384).hexdigest()

        try:
            headers = request_args['headers']
        except KeyError:
            headers = request_args['headers'] = {}

        headers['X-GEMINI-APIKEY'] = self.api_key
        headers['X-GEMINI-PAYLOAD'] = payload
        headers['X-GEMINI-SIGNATURE'] = sig

    # Helper functions and private methods.

