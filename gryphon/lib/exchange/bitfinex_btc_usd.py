# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import hashlib
import hmac
import json
import time

import cdecimal
from cdecimal import Decimal
from delorean import Delorean, parse

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

logger = get_logger(__name__)


class BitfinexBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(BitfinexBTCUSDExchange, self).__init__(session)

        self.name = u'BITFINEX_BTC_USD'
        self.friendly_name = u'Bitfinex BTC-USD'
        self.base_url = 'https://api.bitfinex.com/v1'
        self.currency = 'USD'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.002')
        self.limit_order_fee = Decimal('0.001')
        self.fee = Decimal('0.00')
        self.fiat_balance_tolerance = Money('0.01', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.001', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def req(self, req_method, url, **kwargs):
        req = super(BitfinexBTCUSDExchange, self).req(req_method, url, **kwargs)
        return req

    def resp(self, req):
        response = super(BitfinexBTCUSDExchange, self).resp(req)
        if 'message' in response:
            errors_string = str(response['message'])
            if 'not enough balance' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Order could not be cancelled' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'Nonce is too small' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        return response

    def all_trades(self, until=None):
        req = self.all_trades_req(until)
        return self.all_trades_resp(req)

    def all_trades_req(self, until=None):
        payload = {
            'symbol': 'btcusd',
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

    ######## Common Exchange Methods ########

    # modifies request_args
    def auth_request(self, req_method, url, request_args):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self.load_env('BITFINEX_BTC_USD_API_KEY')
            self.secret = self.load_env('BITFINEX_BTC_USD_API_SECRET')

        endpoint = url.replace(self.base_url, '')
        endpoint = '/v1' + endpoint

        timestamp = int(round(time.time() * 1000))
        nonce = timestamp * 1000 + 1000000000
        logger.debug('Nonce: %s' % nonce)

        try:
            data = request_args['data']
            # payload get passed as a header, so we don't want to POST them
            request_args['data'] = {}
        except KeyError:
            data = {}

        payloadObject = {
            'request':endpoint,
            'nonce':str(nonce),
        }
        payloadObject.update(data)
        payload_json = json.dumps(payloadObject)
        payload = str(base64.b64encode(payload_json))

        sig = hmac.new(self.secret, payload, hashlib.sha384).hexdigest()

        try:
           headers = request_args['headers']
        except KeyError:
           headers = request_args['headers'] = {}

        headers['X-BFX-APIKEY'] = self.api_key
        headers['X-BFX-PAYLOAD'] = payload
        headers['X-BFX-SIGNATURE'] = sig

    def balance_req(self):
        return self.req('get', '/balances')

    def balance_resp(self, req):
        raw_balances = self.resp(req)

        btc_available = None
        usd_available = None
        for raw_balance in raw_balances:
            if raw_balance['type'] == 'exchange':
                if raw_balance['currency'] == 'btc':
                    btc_available = Money(raw_balance['available'], 'BTC')
                elif raw_balance['currency'] == 'usd':
                    usd_available = Money(raw_balance['available'], 'USD')

        if btc_available == None or usd_available == None:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'missing expected balances',
            )

        balance = Balance()
        balance['BTC'] = btc_available
        balance['USD'] = usd_available

        return balance

    def ticker_req(self, verify=True):
        return self.req('get', '/pubticker/btcusd', no_auth=True, verify=verify)

    def ticker_resp(self, req):
        response = self.resp(req)
        return {
            'high': Money(response['high'], 'USD'),
            'low': Money(response['low'], 'USD'),
            'last': Money(response['last_price'], 'USD'),
            'volume': Money(response['volume'], 'BTC')
        }

    def _get_order_book_req(self, verify=True):
        return self.req('get', '/book/btcusd', no_auth=True, verify=verify)

    @property
    def _orderbook_sort_key(self):
        return lambda o: float(o['price'])

    def parse_order(self, order):
        price = Money(order['price'], 'USD')
        volume = Money(order['amount'], 'BTC')
        return (price, volume)

    def create_trade_req(self, mode, volume, price, is_market_order=False):
        side = self.from_const(mode)

        if price.currency != 'USD':
            raise ValueError('price must be in USD')
        if volume.currency != 'BTC':
            raise ValueError('volume must be in BTC')

        volume_str = '%.8f' % volume.amount
        price_str = '%.8f' % price.amount

        payload = {
            'symbol': 'btcusd',
            'amount': volume_str,
            'price': price_str,
            'exchange': 'bitfinex',
            'side': side,
            'type': 'exchange limit',
        }

        if is_market_order == False:
            payload['is_postonly'] = True

        return self.req('post', '/order/new', data=payload)

    def create_trade_resp(self, req):
        response = self.resp(req)
        try:
            order_id = str(response['order_id'])
            return {'success': True, 'order_id': order_id}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order id',
            )

    def open_orders_req(self):
        return self.req('post', '/orders')

    def open_orders_resp(self, req):
        raw_open_orders = self.resp(req)
        open_orders = []

        for raw_order in raw_open_orders:
            mode = self._order_mode_to_const(raw_order['side'])
            volume = Money(raw_order['original_amount'], 'BTC')
            volume_remaining = Money(raw_order['remaining_amount'], 'BTC')

            order = {
                'mode': mode,
                'id': str(raw_order['id']),
                'price': Money(raw_order['price'], 'USD'),
                'volume': volume,
                'volume_remaining': volume_remaining
            }

            open_orders.append(order)

        return open_orders

    def multi_order_details_req(self):
        return self.trades_for_orders_req()

    def multi_order_details_resp(self, req, order_ids):
        order_ids = [unicode(o) for o in order_ids]

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
                    btc_amount = Money(t['amount'], 'BTC')
                    fee = abs(Money(t['fee_amount'], t['fee_currency']))
                    price = Money(t['price'], 'USD')

                    usd_amount = price * btc_amount.amount
                    usd_amount = usd_amount.round_to_decimal_places(
                            8,
                            rounding=cdecimal.ROUND_HALF_UP,
                    )

                    our_type = self._order_mode_to_const(t['type'].lower())

                    total_usd += usd_amount
                    total_btc += btc_amount

                    our_trades.append({
                        'time': int(float(t['timestamp'])),
                        'trade_id': unicode(t['tid']),
                        'fee': fee,
                        'btc': btc_amount,
                        'fiat': usd_amount,
                    })

            try:
                time_created = min([t['time'] for t in our_trades])
            except ValueError: # no trades
                time_created = None

            data[order_id] = {
                'time_created': time_created,
                'type': our_type,
                'btc_total': total_btc,
                'fiat_total': total_usd,
                'trades': our_trades
            }

        return data

    def cancel_order_req(self, order_id):
        payload = {
            'order_id': int(order_id)
        }
        return self.req('post', '/order/cancel', data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)
        # We want to make sure the order is actually cancelled before going on
        time.sleep(2)
        return {'success': True}

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if not isinstance(volume, Money) or volume.currency != 'BTC':
            raise TypeError('Withdrawal volume must be in BTC')

        payload = {
            'withdraw_type': 'bitcoin',
            'walletselected': 'exchange',
            'amount': str(volume.amount),
            'address': address,
        }

        return self.req('post', '/withdraw', data=payload)

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)

        # not sure why this comes back in an array
        # [{u'status': u'error', u'message': u'Insufficient ...', u'withdrawal_id': 0}]
        response = response[0]

        if response['status'] != 'success':
            raise exceptions.ExchangeAPIErrorException(self, response['message'])

        return {'success': True, 'exchange_withdrawal_id': response['withdrawal_id']}

    # returns an OrderedDict of order ids mapped to their filled volume (only include orders that have some trades)
    def audit(self, skip_recent=0):
        orders = OrderedDict()
        trades_to_audit = self.all_trades()
        # Trades from the same order aren't guaranteed to be next to each other, so we need to group them
        trades_to_audit.sort(key=lambda t:(t['order_id'], t['timestamp']), reverse=True)

        # we want to skip recent orders, but splitting between trades will give us incorrect volume_filled
        orders_to_skip = skip_recent

        while orders_to_skip > 0:
            try:
                trade = trades_to_audit.pop(0)
                # we found a boundary
                if trade['order_id'] != trades_to_audit[0]['order_id']:
                    orders_to_skip -= 1
            except IndexError:
                # if we run off the end of the list, we are trying to strip all trades
                trades_to_audit = []
                orders_to_skip = 0

        for trade in trades_to_audit:
            order_id = str(trade['order_id'])

            try:
                orders[order_id] += abs(Money(trade['amount'], 'BTC'))
            except KeyError:
                orders[order_id] = abs(Money(trade['amount'], 'BTC'))

        # Remove the oldest 2 orders, because its trades might be wrapped around a page
        # gap. This would give us an innacurate volume_filled number. We need to remove
        # 2, since there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        min_fee = Money('20', 'USD')
        percentage_fee = deposit_amount * Decimal('0.001') # 0.1%
        return max(min_fee, percentage_fee)

    def fiat_withdrawal_fee(self, withdrawal_amount):
        min_fee = Money('20', 'USD')
        percentage_fee = withdrawal_amount * Decimal('0.0025') # 0.25% for Express Wires
        base_fee = max(min_fee, percentage_fee)

        # This is probably getting added by some intermediary bank between Bitfinex and
        # us.
        extra_fee = Money('21.8', 'USD')

        return base_fee + extra_fee
