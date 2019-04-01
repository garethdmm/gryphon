"""
https://www.bitstamp.net/api/
"""

# -*- coding: utf-8 -*-
from collections import OrderedDict
import hashlib
import hmac
import time

from cdecimal import *
from delorean import Delorean, epoch
from requests_futures.sessions import FuturesSession
from requests_toolbelt.cookies.forgetful import ForgetfulCookieJar

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class BitstampBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        # 2018-4-4: This is a hack for an outstanding issue in our environment that
        # causes bitstamp to reject all but the first requests made with a
        # requests.Session() object. See trello for more information.
        if not session:
            session = FuturesSession(max_workers=10)
            session.cookies = ForgetfulCookieJar()

        super(BitstampBTCUSDExchange, self).__init__(session)

        # Immutable properties.
        # TODO: Check on status of the withdrawal_requests_url (might need a dash).
        # TODO: Check if the withdraw_url is still being used or why it isn't in the
        #   v2 API.
        self.name = u'BITSTAMP_BTC_USD'
        self.friendly_name = u'Bitstamp BTC-USD'
        self.base_url = 'https://www.bitstamp.net/api/v2/'
        self.currency = u'USD'
        self.volume_currency = 'BTC'
        self.price_decimal_precision = 2

        # Configurables defaults.
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.fee = Decimal('0.0005')  # TODO: update these.
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.001', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

        # Endpoints.
        self.ticker_url = 'ticker/btcusd/'
        self.orderbook_url = 'order_book/btcusd/'
        self.buy_url = 'buy/btcusd/'
        self.sell_url = 'sell/btcusd/'
        self.open_orders_url = 'open_orders/btcusd/'
        self.trade_status_url = 'user_transactions/btcusd/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'
        self.withdrawl_requests_url = 'withdrawal_requests/'
        self.withdraw_url = 'https://priv-api.bitstamp.net/api/bitcoin_withdrawal/'
 
    def resp(self, req):
        response = super(BitstampBTCUSDExchange, self).resp(req)

        try:
            errors = response.get('error', None)
        except AttributeError: # Some endpoints return a list.
            errors = None

        if errors:
            errors_string = str(errors)

            if 'You have only' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Order not found' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'Minimum order size' in errors_string:
                raise exceptions.MinimumOrderSizeError()
            elif 'Invalid nonce' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        return response

    def get_ticker_req(self, verify=True):
        return self.req('get', self.ticker_url, no_auth=True, verify=verify)

    def get_ticker_resp(self, req):
        response = self.resp(req)

        return {
            'high': Money(response['high'], self.currency),
            'low': Money(response['low'], self.currency),
            'last': Money(response['last'], self.currency),
            'volume': Money(response['volume'], self.volume_currency)
        }

    def order_is_open(self, order_id):
        order_id = unicode(order_id)
        open_orders = self.open_orders()
        matching_orders = [o for o in open_orders if unicode(o.get('id')) == order_id]
        is_open = len(matching_orders) > 0

        return is_open

    def all_transactions(self, page=0):
        req = self.all_transactions_req(page=page)
        return self.all_transactions_resp(req)

    def all_transactions_req(self, page=0):
        offset = page * 100
        payload = {
            'offset': offset,
        }

        return self.req('post', self.trade_status_url, data=payload)

    def all_transactions_resp(self, req):
        return self.resp(req)

    def all_trades(self, page=0):
        req = self.all_trades_req(page=page)
        return self.all_trades_resp(req)

    def all_trades_req(self, page=0):
        return self.all_transactions_req(page=page)

    def all_trades_resp(self, req):
        transactions = self.all_transactions_resp(req)
        trades = [t for t in transactions if t['type'] == '2']

        return trades

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
                if oid not in matching_trades:
                    matching_trades[oid] = []

                matching_trades[oid].append(trade)

        return matching_trades

    ###### Common Exchange Methods ######

    def load_creds(self):
        try:
            self.api_key
            self.secret
            self.client_id
        except AttributeError:
            self.api_key = self._load_env('%s_API_KEY' % self.name)
            self.secret = self._load_env('%s_API_SECRET' % self.name)
            self.client_id = self._load_env('%s_CLIENT_ID' % self.name)

    def auth_request(self, req_method, url, request_args):
        """
        modifies request_args
        """
        self.load_creds()

        try:
            payload = request_args['data']
        except KeyError:
            payload = request_args['data'] = {}

        # TODO: fix nonce collisions
        nonce = unicode(int(round(time.time() * 1000)))
        message = nonce + self.client_id + self.api_key

        sig = hmac.new(
            self.secret,
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest().upper()

        payload.update({
            'nonce': nonce,
            'key': self.api_key,
            'signature': sig,
        })

    def get_balance_req(self):
        return self.req('post', self.balance_url)

    def get_balance_resp(self, req):
        response = self.resp(req)
        balance = Balance()

        try:
            vol_currency_key = '%s_available' % self.volume_currency.lower()
            price_currency_key = '%s_available' % self.currency.lower()

            balance[self.volume_currency] = Money(
                response[vol_currency_key],
                self.volume_currency,
            )

            balance[self.currency] = Money(response[price_currency_key], self.currency)
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'Balance missing expected keys',
            )

        return balance

    def _get_orderbook_from_api_req(self, verify=True):
        return self.req('get', self.orderbook_url, no_auth=True, verify=verify)

    def _get_orderbook_from_api_resp(self, req):
        order_book = self.resp(req)

        timestamp = int(order_book['timestamp'])
        now = Delorean()

        if epoch(timestamp) < now.last_minute(10):
            raise exceptions.ExchangeAPIErrorException(
                self, 
                'Orderbook is more than 10 minutes old',
            )

        return order_book

    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        if mode == Consts.ASK:
            url = self.sell_url
        elif mode == Consts.BID:
            url = self.buy_url
        else:
            raise ValueError('mode must be one of ask/bid')

        # This is required by Bitstamp API.
        price = price.round_to_decimal_places(2) # Max is 7 digits.
        volume = volume.round_to_decimal_places(8) # Max is 8 decimal places.

        try:
            payload = {
                'amount': volume.amount,
                'price': price.amount
            }
        except AttributeError:
            raise TypeError('volume and price must be Money objects')

        return self.req('post', url, data=payload)

    def place_order_resp(self, req):
        response = self.resp(req)

        try:
            return {'success': True, 'order_id': unicode(response['id'])}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order id',
            )

    def get_open_orders_req(self):
        return self.req('post', self.open_orders_url)

    def get_open_orders_resp(self, req):
        raw_open_orders = self.resp(req)
        open_orders = []

        for raw_order in raw_open_orders:
            if raw_order['type'] == '0':
                mode = Consts.BID
            elif raw_order['type'] == '1':
                mode = Consts.ASK

            usd_price = Money(raw_order['price'], self.currency)
            order = {
                'mode': mode,
                'id': str(raw_order['id']),
                'price': usd_price,
                'volume_remaining': Money(raw_order['amount'], self.volume_currency),
            }

            open_orders.append(order)

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
        order_ids = [unicode(o) for o in order_ids]

        multi_trades = self.trades_for_orders_resp(req, order_ids)
        data = {}

        for order_id in order_ids:
            total_price_currency = Money('0', self.currency)
            total_volume_currency = Money('0', self.volume_currency)
            our_trades = []
            our_type = None

            price_currency_key = self.currency.lower()
            vol_currency_key = self.volume_currency.lower()

            if order_id in multi_trades:
                trades = multi_trades[order_id]

                for t in trades:
                    volume_currency_amount = abs(
                        Money(t[vol_currency_key], self.volume_currency),
                    )

                    fee = abs(Money(t['fee'], self.currency))

                    price_currency_amount = abs(
                        Money(t[price_currency_key], self.currency),
                    )

                    total_price_currency += price_currency_amount
                    total_volume_currency += volume_currency_amount

                    if Decimal(t[vol_currency_key]) > 0:
                        our_type = Consts.BID
                    else:
                        our_type = Consts.ASK

                    our_trades.append({
                        'time': int(parse(t['datetime']).epoch),
                        'trade_id': unicode(t['id']),
                        'fee': fee,
                        vol_currency_key: volume_currency_amount,
                        'fiat': price_currency_amount,
                    })

            try:
                time_created = min([t['time'] for t in our_trades])
            except ValueError: # This is raised if there are no trades.
                time_created = None

            data[order_id] = {
                'time_created': time_created,
                'type': our_type,
                '%s_total' % vol_currency_key: total_volume_currency,
                'fiat_total': total_price_currency,
                'trades': our_trades,
            }

        return data

    def cancel_order_req(self, order_id):
        payload = {
            'id': order_id,
        }

        return self.req('post', self.trade_cancel_url, data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)
        return {'success': True}

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if (not isinstance(volume, Money)
                or volume.currency != self.volume_currency):
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        payload = {
            'amount': volume.amount,
            'address': address,
        }

        return self.req('post', self.withdraw_url, data=payload)

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)
        return {'success': True}

    def get_order_audit_data(self, skip_recent=0):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (including
        only orders that have some trades).
        """
        orders = OrderedDict()
        trades_to_audit = self.all_trades()

        # Trades from the same order aren't guaranteed to be next to each other, so we
        # need to group them.
        trades_to_audit.sort(key=lambda t: (t['order_id'], t['datetime']), reverse=True)

        # We want to skip recent orders, but splitting between transactions will give
        # us incorrect volume_filled.
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

        for transaction in trades_to_audit:
            # If transaction is a trade
            if transaction['type'] == 2:
                order_id = str(transaction['order_id'])

                try:
                    orders[order_id] += abs(
                        Money(transaction[self.vol_currency_key], self.volume_currency),
                    )
                except KeyError:
                    orders[order_id] = abs(
                        Money(transaction[self.vol_currency_key], self.volume_currency),
                    )

        # Remove the two oldest orders, because its trades might be wrapped around a
        # bitstamp page gap, and this would give us an innacurate volume_filled number.
        # We need to remove two because there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        min_fee = Money('7.5', self.currency)
        percentage_fee = deposit_amount * Decimal('0.0005') # 0.05%

        # As of September 2016 we're getting charged an extra $15 on deposits. Bitstamp
        # says it isn't them so it's likely an intermediary bank. TODO look into this
        # with BMO.
        intermediary_fee = Money('15', self.currency)

        return max(min_fee, percentage_fee) + intermediary_fee

    def fiat_withdrawal_fee(self, withdrawal_amount):
        min_fee = Money('15', 'USD')
        percentage_fee = withdrawal_amount * Decimal('0.0009') # 0.09%

        return max(min_fee, percentage_fee)
