# We need to use absolute_import so we can load the coinbase pip module without
# conflicting with our filename of coinbase.py.
from __future__ import absolute_import
import os
import base64
from collections import OrderedDict
import hashlib
import hmac
import json
import time
import urllib

from cdecimal import Decimal
import coinbase.client

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class CoinbaseBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(CoinbaseBTCUSDExchange, self).__init__(session)

        self.name = u'COINBASE_BTC_USD'
        self.friendly_name = u'Coinbase BTC-USD'
        self.base_url = 'https://api.gdax.com'
        self.currency = 'USD'
        self.bid_string = 'buy'
        self.ask_string = 'sell'
        self.product_id = 'BTC-USD'
        self.price_decimal_precision = 2

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.0022') # Updated by Gareth on 2016-9-20
        self.limit_order_fee = Decimal('0.001')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.001', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def req(self, req_method, url, **kwargs):
        try:
            kwargs['data'] = json.dumps(kwargs['data'])
        except KeyError:
            kwargs['data'] = '{}'

        kwargs['headers'] = {'Content-Type': 'application/json'}
        req = super(CoinbaseBTCUSDExchange, self).req(req_method, url, **kwargs)

        return req

    def resp(self, req):
        response = req.result()

        try:
            data = response.json(parse_float=Decimal)
        except ValueError:
            raise exceptions.ExchangeAPIFailureException(self, response)

        headers = response.headers

        if response.status_code < 200 or response.status_code >= 300:
            try:
                error_string = data['message']
            except KeyError:
                error_string = str(data)

            error_string = error_string.lower()

            if 'notfound' in error_string:
                raise exceptions.NoEffectOrderCancelledError()
            elif ('order already done' in error_string or
                    'order not found' in error_string):
                raise exceptions.CancelOrderNotFoundError()
            elif 'order size is too small' in error_string:
                raise exceptions.MinimumOrderSizeError()
            elif 'insufficient funds' in error_string:
                raise exceptions.InsufficientFundsError()
            # These errors occur randomly (usually when Coinbase under heavy load).
            # We want to return an ExchangeAPIFailureException so that requests get
            # retried.
            elif ('request timestamp expired' in error_string or
                    'internal server error' in error_string):
                raise exceptions.ExchangeAPIFailureException(self, response)
            else:
                raise exceptions.ExchangeAPIErrorException(self, error_string)
        else:
            return data, headers

    def pagination_cursors(self, headers):
        return {
            'prev_cursor': headers.get('CB-BEFORE'),
            'next_cursor': headers.get('CB-AFTER')
        }

    def ledger(self, account_id=None, return_pagination=False, next_cursor=None):
        req = self.ledger_req(account_id, next_cursor=next_cursor)
        return self.ledger_resp(req, return_pagination=return_pagination)

    def ledger_req(self, account_id=None, next_cursor=None):
        if not account_id:
            account_id = self.load_fiat_account_id()

        params = {}

        if next_cursor:
            params['after'] = next_cursor

        endpoint = '/accounts/%s/ledger' % account_id

        if params:
            endpoint += '?%s' % urllib.urlencode(params)

        return self.req('get', endpoint)

    def ledger_resp(self, req, return_pagination=False):
        response, headers = self.resp(req)

        if return_pagination:
            return response, self.pagination_cursors(headers)
        else:
            return response

    def _get_recent_trades(self, order_id=None, return_pagination=False, next_cursor=None):
        req = self._get_recent_trades_req(order_id, next_cursor=next_cursor)
        return self._get_recent_trades_resp(req, return_pagination=return_pagination)

    def _get_recent_trades_req(self, order_id=None, next_cursor=None):
        params = {
            'product_id': self.product_id
        }

        if order_id:
            params['order_id'] = order_id

        if next_cursor:
            params['after'] = next_cursor

        endpoint = '/fills?%s' % urllib.urlencode(params)

        return self.req('get', endpoint)

    def _get_recent_trades_resp(self, req, return_pagination=False):
        response, headers = self.resp(req)
        trades = []

        for trade in response:
            if not trade['settled']:
                continue

            price = Money(trade['price'], self.currency)
            size = Money(trade['size'], 'BTC')
            fiat = price * size.amount
            our_type = self._order_mode_to_const(trade['side'])

            # Strange bug here, delorean isn't parsing the trailing Z on the created_at
            # date correctly.
            trade_dict = {
                'time': int(parse(trade['created_at'][:-1]).epoch),
                'trade_id': str(trade['trade_id']),
                'order_id': str(trade['order_id']),
                'btc': size,
                'fiat': fiat,
                'fee': Money(trade['fee'], self.currency),
                'type': our_type,
            }

            trades.append(trade_dict)

        if return_pagination:
            return trades, self.pagination_cursors(headers)
        else:
            return trades

    def transfer(self, transfer_type, btc_amount, coinbase_account_id):
        req = self.transfer_req(transfer_type, btc_amount, coinbase_account_id)
        return self.transfer_resp(req)

    def transfer_req(self, transfer_type, btc_amount, coinbase_account_id):
        payload = {
            'type': transfer_type,
            'amount': str(btc_amount.amount),
            'coinbase_account_id': coinbase_account_id
        }

        return self.req('post', '/transfers', data=payload)

    def transfer_resp(self, req):
        response, headers = self.resp(req)
        return response

    def load_wallet_creds(self):
        try:
            self.wallet_api_key
            self.wallet_api_secret
            self.wallet_id
        except AttributeError:
            self.wallet_api_key = self._load_env('COINBASE_BTC_USD_WALLET_API_KEY')
            self.wallet_api_secret = self._load_env('COINBASE_BTC_USD_WALLET_API_SECRET')
            self.wallet_id = self._load_env('COINBASE_BTC_USD_WALLET_ID')

    def load_fiat_account_id(self):
        return self._load_env('COINBASE_BTC_USD_FIAT_ACCOUNT_ID')

    @property
    def wallet_api_client(self):
        """API Client for the regular Coinbase Wallet (not the exchange API)"""
        if hasattr(self, '_wallet_api_client'):
            return self._wallet_api_client
        else:
            self.load_wallet_creds()
            self._wallet_api_client = coinbase.client.Client(
                self.wallet_api_key,
                self.wallet_api_secret,
            )

            return self._wallet_api_client

    def get_wallet(self):
        self.load_wallet_creds()
        return self.wallet_api_client.get_account(self.wallet_id)

    def transfer_wallet_balance_into_exchange(self):
        wallet = self.get_wallet()
        balance = Money(wallet.balance.amount, wallet.balance.currency)
        if balance > 0:
            self.transfer('deposit', balance, wallet.id)

    def check_for_daily_fee_rebate(self, exchange_data):
        recent_transactions = self.ledger()
        rebates = [tx for tx in recent_transactions if tx['type'] == 'rebate']

        for rebate in rebates:
            rebate_id = rebate['details']['rebate_id']

            # Searching transaction_details for the rebate_id is pretty janky but we
            # need to figure out a strategy for handling rebates anyways so this is
            # good enough for now.
            search_string = '%{}%'.format(rebate_id)
            existing_rebate_transaction = exchange_data.transactions\
                .filter(Transaction._transaction_details.like('%fee rebate%'))\
                .filter(Transaction._transaction_details.like(search_string))\
                .first()

            if existing_rebate_transaction:
                logger.debug('Found rebate, but it has already been recorded (%s)' % rebate_id)
                continue

            amount = Money(rebate['amount'], self.currency)

            logger.debug('Recording rebate for %s' % amount)

            transaction_details = {
                'notes': 'fee rebate',
                'rebate_id': rebate_id,
            }

            deposit = Transaction(
                Transaction.DEPOSIT,
                Transaction.IN_TRANSIT,
                amount,
                exchange_data,
                transaction_details,
            )
            # We deliberately leave the deposit IN_TRANSIT, and the next audit will see
            # the balance change and COMPLETE it through the regular deposit_landed
            # flow.

    # Common Exchange Methods

    def load_creds(self):
        try:
            self.api_key
            self.secret
            self.passphrase
        except AttributeError:
            self.api_key = self._load_env('COINBASE_BTC_USD_API_KEY')
            self.passphrase = self._load_env('COINBASE_BTC_USD_API_PASSPHRASE')
            self.secret = self._load_env('COINBASE_BTC_USD_API_SECRET')

    def auth_request(self, req_method, url, request_args):
        """
        This modifies request_args.
        """
        self.load_creds()

        req_method = req_method.upper()
        timestamp = unicode(int(round(time.time())))

        # This has already been dumped to json by req().
        body = request_args['data']

        endpoint = url.replace(self.base_url, '')

        data = timestamp + req_method + endpoint + body
        key = base64.b64decode(self.secret)
        sig = base64.b64encode(hmac.new(key, data, hashlib.sha256).digest())

        try:
            headers = request_args['headers']
        except KeyError:
            headers = request_args['headers'] = {}

        headers.update({
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': sig,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'CB-ACCESS-TIMESTAMP': timestamp
        })

    def get_balance_req(self):
        return self.req('get', '/accounts')

    def get_balance_resp(self, req):
        response, headers = self.resp(req)

        balance = Balance()

        try:
            for account in response:
                if account['currency'] == 'BTC':
                    balance['BTC'] = Money(account['available'], 'BTC')
                elif account['currency'] == self.currency:
                    balance[self.currency] = Money(account['available'], self.currency)
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(self, 'malformed response')

        return balance

    def get_ticker_req(self, verify=True):
        return self.req(
            'get',
            '/products/%s/stats' % self.product_id,
            no_auth=True,
            verify=verify,
        )

    def get_ticker_resp(self, req):
        response, headers = self.resp(req)

        return {
            'high': Money(response['high'], self.currency),
            'low': Money(response['low'], self.currency),
            'last': None,
            'volume': Money(response['volume'], 'BTC')
        }

    def _get_orderbook_from_api_req(self, verify=True):
        orderbook_url = '/products/%s/book?level=3' % self.product_id
        return self.req('get', orderbook_url, no_auth=True, verify=verify)

    def _get_orderbook_from_api_resp(self, req):
        response, headers = self.resp(req)
        return response

    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        mode = self._order_mode_from_const(mode)

        if price.currency != self.currency:
            raise ValueError('price must be in %s' % self.currency)
        if volume.currency != 'BTC':
            raise ValueError('volume must be in BTC')

        volume_str = '%.8f' % volume.amount
        price_str = '%.2f' % price.amount

        payload = {
            'product_id': self.product_id,
            'side': mode,
            'size': volume_str,
            'price': price_str,
        }

        if order_type == order_types.POST_ONLY:
            payload['post_only'] = True

        return self.req('post', '/orders', data=payload)

    def place_order_resp(self, req):
        response, headers = self.resp(req)
        order_id = response['id']

        return {'success': True, 'order_id': order_id}

    def get_open_orders_req(self):
        return self.req('get', '/orders')

    def get_open_orders_resp(self, req):
        raw_open_orders, headers = self.resp(req)
        open_orders = []

        for raw_order in raw_open_orders:
            mode = self._order_mode_to_const(raw_order['side'])
            volume = Money(raw_order['size'], 'BTC')
            volume_executed = Money(raw_order['filled_size'], 'BTC')
            volume_remaining = volume - volume_executed
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
        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req)

    def get_order_details_req(self, order_id):
        reqs = {}
        endpoint = '/orders/%s' % order_id
        reqs['order'] = (self.req('get', endpoint))

        # This kind of breaks the req/resp paradigm, but we need to get the results of
        # each batch before we know if we need to fetch another batch.
        trades = []

        trade_batch, pagination = self._get_recent_trades(
            order_id,
            return_pagination=True,
        )

        trades += trade_batch

        # Getting < 100 trades back means we have reached the end.
        while len(trade_batch) >= 100:
            time.sleep(1)

            trade_batch, pagination = self._get_recent_trades(
                order_id,
                return_pagination=True,
                next_cursor=pagination['next_cursor'],
            )

            trades += trade_batch

        # Instead of returning the requests, we return the results since we have them
        # already.
        reqs['trades'] = trades

        return reqs

    def get_order_details_resp(self, reqs):
        try:
            raw_order, headers = self.resp(reqs['order'])
        except exceptions.NoEffectOrderCancelledError:
            # Coinbase returns an API Error with the text "NotFound" in it when
            # querying orders that were cancelled with no trades, so we return an empty
            # order here if that is the response.
            result = {
                'time_created': None,
                'type': None,
                'btc_total': Money('0', self.volume_currency),
                'fiat_total': Money('0', self.currency),
                'trades': [],
            }

            return result

        # This already has the results (see above) so we don't need to .resp() it
        our_trades = reqs['trades']

        mode = self._order_mode_to_const(raw_order['side'])
        total_btc = Money(raw_order['filled_size'], 'BTC')
        time_created = int(parse(raw_order['created_at']).epoch)
        total_fiat = Money('0', self.currency)

        for t in our_trades:
            total_fiat += t['fiat']

        result = {
            'time_created': time_created,
            'type': mode,
            'btc_total': total_btc,
            'fiat_total': total_fiat,
            'trades': our_trades
        }

        return result

    def get_multi_order_details_req(self, order_ids):
        data = {}

        for oid in order_ids:
            data[oid] = self.get_order_details_req(oid)
            time.sleep(1) # 1 r/s rate limits :(

        return data

    def get_multi_order_details_resp(self, reqs):
        data = {}

        for oid in reqs:
            data[oid] = self.get_order_details_resp(reqs[oid])

        return data

    def cancel_order_req(self, order_id):
        endpoint = '/orders/%s' % order_id
        return self.req('delete', endpoint)

    def cancel_order_resp(self, req):
        # This is a weird one. It doesn't return JSON on success so we can't use
        # regular self.resp().
        response = req.result()

        if response.status_code == 200 and response.text == 'OK':
            return {'success': True}
        else:
            # This exception logic is more complicated than it appears.
            # If an order had no effect (no fills), cancelling it twice will
            # give back the 'notfound' response from coinbase, which raises
            # NoEffectOrderCancelledError, but the bots expect a double cancel
            # to raise CancelOrderNotFoundError, so here we catch the first
            # exception and raise the second. If the order has fllls on it,
            # the response from coinbase will raise CancelOrderNotFoundError
            # in self.resp naturally.
            try:
                resp = self.resp(req)
            except exceptions.NoEffectOrderCancelledError:
                raise exceptions.CancelOrderNotFoundError()

    def withdraw_crypto(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if not isinstance(volume, Money) or volume.currency != 'BTC':
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        # Step 1: Withdraw from exchange to wallet.
        wallet = self.get_wallet()
        self.transfer('withdraw', volume, wallet.id)

        # Step 2: Send from wallet to address.
        response = wallet.send_money(address, str(volume.amount))
        tx = response['hsh']

        return {'success': True, 'tx': tx}

    def pre_audit(self, exchange_data):
        # As soon as deposits land in our wallet, we want to transfer them into the
        # exchange.
        # TODO: rehabilitate these.
        # self.transfer_wallet_balance_into_exchange()
        # self.check_for_daily_fee_rebate(exchange_data)
        pass

    def get_order_audit_data(self, skip_recent=0, lookback_pages=1):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (only include
        orders that have some trades).
        """
        orders = OrderedDict()

        trades_to_audit, pagination = self._get_recent_trades(return_pagination=True)
        current_page = 1

        while current_page < lookback_pages:
            batch, pagination = self._get_recent_trades(
                next_cursor=pagination['next_cursor'],
                return_pagination=True,
            )

            trades_to_audit += batch
            current_page += 1

        # Trades from the same order aren't guaranteed to be next to each other, so we
        # need to group them.
        trades_to_audit.sort(key=lambda t: (t['time']), reverse=True)

        for trade in trades_to_audit:
            order_id = str(trade['order_id'])

            try:
                orders[order_id] += abs(trade['btc'])
            except KeyError:
                orders[order_id] = abs(trade['btc'])

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
        return Money('25', 'USD')

    def fiat_withdrawal_fee(self, withdrawal_amount):
        coinbase_fee = Money('40', 'USD')
        bmo_fee = Money('20', 'USD')

        return coinbase_fee + bmo_fee
