"""
Exchange documentation: https://api.itbit.com/docs
"""

# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict, defaultdict
import hashlib
import hmac
import json
import time
import urllib

import cdecimal
from cdecimal import Decimal

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class ItbitBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(ItbitBTCUSDExchange, self).__init__(session)

        self.name = u'ITBIT_BTC_USD'
        self.friendly_name = u'Itbit BTC-USD'
        self.base_url = 'https://api.itbit.com/v1'
        self.currency = 'USD'
        self.bid_string = 'buy'
        self.ask_string = 'sell'
        self.nonce = 1

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.002')
        self.limit_order_fee = Decimal('0')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    @property
    def wallet_id(self):
        try:
            self._wallet_id
        except AttributeError:
            self._wallet_id = self._load_env('ITBIT_BTC_USD_WALLET_ID')

        return self._wallet_id

    def req(self, req_method, url, **kwargs):
        # Our auth_request method expects the params in the url.
        assert '?' not in url

        if 'params' in kwargs:
            if kwargs['params']: # Check that it's not empty.
                url += '?' + urllib.urlencode(kwargs['params'])

            del kwargs['params']

        req = super(ItbitBTCUSDExchange, self).req(req_method, url, **kwargs)

        return req

    def resp(self, req):
        response = super(ItbitBTCUSDExchange, self).resp(req)

        if 'error' in response and response['error']:
            raise exceptions.ExchangeAPIErrorException(self, response['error'])

        if 'code' in response:
            errors_string = str(response['description'])
            error_code = int(response['code'])

            if error_code == 81001:
                raise exceptions.InsufficientFundsError()
            elif error_code == 10002:
                raise exceptions.NonceError()
            elif error_code == 81002:
                raise exceptions.CancelOrderNotFoundError()
            else:
                raise exceptions.ExchangeAPIErrorException(
                    self,
                    'Code %s: %s' % (
                    error_code, errors_string,
                ))

        return response

    def all_trades(self, page=1):
        req = self.all_trades_req(page)
        return self.all_trades_resp(req)

    def all_trades_req(self, page=1):
        params = {}

        if page:
            params['page'] = page

        return self.req(
            'get',
            '/wallets/%s/trades' % self.wallet_id,
            params=params,
        )

    def all_trades_resp(self, req):
        response = self.resp(req)
        return response['tradingHistory']

    def trades_for_orders(self, order_ids):
        req = self.trades_for_orders_req()
        return self.trades_for_orders_resp(req, order_ids)

    def trades_for_orders_req(self):
        return self.all_trades_req()

    def trades_for_orders_resp(self, req, order_ids):
        order_ids = [str(o) for o in order_ids]
        trades = self.all_trades_resp(req)

        matching_trades = defaultdict(list)

        for trade in trades:
            oid = str(trade['orderId'])

            if oid in order_ids:
                matching_trades[oid].append(trade)

        return matching_trades

    def all_orders(self, status=None, page=1):
        req = self.all_orders_req(status, page)
        return self.all_orders_resp(req)

    def all_orders_req(self, status=None, page=1):
        params = {}

        if status:
            params['status'] = status
        if page:
            params['page'] = page

        return self.req(
            'get',
            '/wallets/%s/orders' % self.wallet_id,
            params=params,
        )

    def all_orders_resp(self, req):
        raw_orders = self.resp(req)
        orders = []

        for raw_order in raw_orders:
            mode = self._order_mode_to_const(raw_order['side'])
            volume = Money(raw_order['amount'], 'BTC')
            volume_filled = Money(raw_order['amountFilled'], 'BTC')
            volume_remaining = volume - volume_filled

            order = {
                'mode': mode,
                'id': str(raw_order['id']),
                'price': Money(raw_order['price'], 'USD'),
                'volume': volume,
                'volume_remaining': volume_remaining,
                'status': raw_order['status']
            }

            orders.append(order)

        return orders

    # Common Exchange Methods

    def auth_request(self, req_method, url, request_args):
        """
        This modifies request_args.
        """
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('ITBIT_BTC_USD_API_KEY')
            self.secret = self._load_env('ITBIT_BTC_USD_API_SECRET').encode('utf-8')

        timestamp = int(round(time.time() * 1000))
        nonce = self.nonce

        body = ''

        if 'data' in request_args:
            body = json.dumps(request_args['data'])

        request_args['data'] = body

        message = self._auth_create_message(req_method, url, body, nonce, timestamp)

        sig = self._auth_sign_message(message, nonce, url, self.secret)

        if 'headers' not in request_args:
            request_args['headers'] = {}

        headers = request_args['headers']

        headers['Authorization'] = self.api_key + ':' + sig
        headers['X-Auth-Timestamp'] = str(timestamp)
        headers['X-Auth-Nonce'] = str(nonce)
        headers['Content-Type'] = 'application/json'

    def _auth_create_message(self, verb, url, body, nonce, timestamp):
        return json.dumps(
            [verb.upper(), url, body, str(nonce), str(timestamp)],
            separators=(',', ':'),
        )

    def _auth_sign_message(self, message, nonce, url, api_secret):
        sha256_hash = hashlib.sha256()
        nonced_message = str(nonce) + message
        sha256_hash.update(nonced_message)
        hash_digest = sha256_hash.digest()

        msg_to_hmac = url.encode('utf8') + hash_digest
        hmac_digest = hmac.new(api_secret, msg_to_hmac, hashlib.sha512).digest()

        sig = base64.b64encode(hmac_digest)

        return sig

    def get_balance_req(self):
        try:
            self.user_id
        except AttributeError:
            self.user_id = self._load_env('ITBIT_BTC_USD_USER_ID')

        return self.req('get', '/wallets/%s' % self.wallet_id)

    def get_balance_resp(self, req):
        response = self.resp(req)
        raw_balances = response['balances']

        btc_available = None
        usd_available = None

        for raw_balance in raw_balances:
            if raw_balance['currency'] == 'XBT':
                btc_available = Money(raw_balance['availableBalance'], 'BTC')
            elif raw_balance['currency'] == 'USD':
                usd_available = Money(raw_balance['availableBalance'], 'USD')

        if btc_available is None or usd_available is None:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'missing expected balances',
            )

        balance = Balance()
        balance['BTC'] = btc_available
        balance['USD'] = usd_available

        return balance

    def get_ticker_req(self, verify=True):
        return self.req(
            'get',
            '/markets/XBTUSD/ticker',
            no_auth=True,
            verify=verify,
        )

    def get_ticker_resp(self, req):
        response = self.resp(req)

        return {
            'high': Money(response['high24h'], 'USD'),
            'low': Money(response['low24h'], 'USD'),
            'last': Money(response['lastPrice'], 'USD'),
            'volume': Money(response['volume24h'], 'BTC')
        }

    def _get_orderbook_from_api_req(self, verify=True):
        return self.req(
            'get',
            '/markets/XBTUSD/order_book',
            no_auth=True,
            verify=verify,
        )

    def place_order_req(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER):
        side = self._order_mode_from_const(mode)

        if price.currency != 'USD':
            raise ValueError('price must be in USD')
        if volume.currency != 'BTC':
            raise ValueError('volume must be in BTC')

        # Truncate the volume instead of rounding it because it's better# to trade too
        # little than too much.
        volume = volume.round_to_decimal_places(2, rounding=cdecimal.ROUND_DOWN)

        volume_str = '%.2f' % volume.amount
        price_str = '%.2f' % price.amount

        payload = {
            'type': 'limit',
            'currency': 'XBT',
            'side': side,
            'amount': volume_str,
            'price': price_str,
            'instrument': 'XBTUSD'
        }

        return self.req(
            'post',
            '/wallets/%s/orders/' % self.wallet_id,
            data=payload,
        )

    def place_order_resp(self, req):
        response = self.resp(req)

        try:
            order_id = str(response['id'])
            return {'success': True, 'order_id': order_id}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order id',
            )

    def get_open_orders_req(self):
        return self.all_orders_req(status='open')

    def get_open_orders_resp(self, req):
        open_orders = self.all_orders_resp(req)

        for o in open_orders:
            del o['status']

        return open_orders

    def get_order_details(self, order_id):
        req = self.get_order_details_req()
        return self.get_order_details_resp(req, order_id)

    def get_order_details_req(self):
        return self.get_multi_order_details_req()

    def get_order_details_resp(self, req, order_id):
        return self.get_multi_order_details_resp(req, [order_id])[order_id]

    def get_multi_order_details(self, order_ids):
        req = self.get_multi_order_details_req()
        return self.get_multi_order_details_resp(req, order_ids)

    def get_multi_order_details_req(self):
        return self.trades_for_orders_req()

    def get_multi_order_details_resp(self, req, order_ids):
        # This is modeled after Bitstamp, where we get the order details from the
        # trades endpoint directly. The caveat is that order_details will only work
        # for the most recent 50 trades. Since we are always accounting trades right
        # after they happen, this should be ok (and also affects Bitstamp).
        order_ids = [str(o) for o in order_ids]

        multi_trades = self.trades_for_orders_resp(req, order_ids)
        data = {}

        for order_id in order_ids:
            total_usd = Money('0', 'USD')
            total_btc = Money('0', 'BTC')

            our_trades = []
            our_type = None

            if order_id in multi_trades:
                trades = multi_trades[order_id]

                for t in trades:
                    assert(t['currency1'] == 'XBT')
                    btc_amount = Money(t['currency1Amount'], 'BTC')

                    assert(t['currency2'] == 'USD')
                    usd_amount = Money(t['currency2Amount'], 'USD')

                    # This might also come back as XBT, but since ItBit has 0-fee
                    # trading right now, I can't tell.
                    assert(t['commissionCurrency'] == 'USD')
                    fee = Money(t['commissionPaid'], 'USD')

                    total_usd += usd_amount
                    total_btc += btc_amount

                    our_type = self._order_mode_to_const(t['direction'])

                    our_trades.append({
                        'time': parse(t['timestamp']).epoch,
                        'trade_id': None,
                        'fee': fee,
                        'btc': btc_amount,
                        'fiat': usd_amount,
                    })

            time_created = None

            if our_trades:
                time_created = min([t['time'] for t in our_trades])

            data[order_id] = {
                'time_created': time_created,
                'type': our_type,
                'btc_total': total_btc,
                'fiat_total': total_usd,
                'trades': our_trades
            }

        return data

    def cancel_order_req(self, order_id):
        return self.req(
            'delete',
            '/wallets/%s/orders/%s' % (self.wallet_id, order_id),
        )

    def cancel_order_resp(self, req):
        # In the success case, no response is given but we need to call resp() so it
        # can catch any error cases.
        response = self.resp(req)  # noqa
        return {'success': True}

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        volume_str = '%.8f' % volume.amount

        payload = {
            'currency': 'XBT',
            'amount': volume_str,
            'address': address,
        }

        return self.req(
            'post',
            '/wallets/%s/cryptocurrency_withdrawals' % self.wallet_id,
            data=payload,
        )

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)
        return {'success': True, 'exchange_withdrawal_id': response['withdrawalId']}

    def get_order_audit_data(self, skip_recent=0, page=1):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (only include
        orders that have some trades).
        Dropped the skip_recent flag because we don't seem to be using it anywhere.
        """
        if skip_recent != 0:
            raise ValueEror('skip_recent is deprecated')

        orders = OrderedDict()
        trades_to_audit = self.all_trades(page=page)

        for trade in trades_to_audit:
            order_id = str(trade['orderId'])

            assert(trade['currency1'] == 'XBT')
            trade_amount = abs(Money(trade['currency1Amount'], 'BTC'))

            try:
                orders[order_id] += trade_amount
            except KeyError:
                orders[order_id] = trade_amount

        # Remove the oldest 2 orders, because its trades might be wrapped around a
        # page gap and this would give us an innacurate volume_filled number.
        # We need to remove 2 because there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        return Money('5', 'USD')

    def fiat_withdrawal_fee(self, withdrawal_amount):
        """
        Itbit fee is from their documentation, and an extra $15 is being charged to us
        before it shows up in our bank account (as of the September 2016), so I assume
        that's an intermediary fee.

        The fee should be a flat $50 on withdrawals > $10k, but we'll see.
        """
        fee = Money('0', 'USD')

        if withdrawal_amount < Money('10,000', 'USD'):
            itbit_fee = Money('15', 'USD')
            intermediary_fee = Money('15', 'USD')

            fee = itbit_fee + intermediary_fee
        else:
            fee = Money('50', 'USD')

        return fee
