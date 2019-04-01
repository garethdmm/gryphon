# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import hashlib
import hmac
import os
import time
import urllib

from cdecimal import Decimal
from delorean import Delorean
from more_itertools import chunked

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

logger = get_logger(__name__)


class LedgerSizeException(Exception):
    pass


class KrakenBTCEURExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(KrakenBTCEURExchange, self).__init__(session, configuration)

        # Immutable properties and endpoints.
        self.name = u'KRAKEN_BTC_EUR'
        self.friendly_name = u'Kraken BTC-EUR'
        self.base_url = 'https://api.kraken.com/0'
        self.price_decimal_precision = 1
        self.currency = u'EUR'
        self.volume_currency = u'BTC'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        self.orderbook_depth = 100000

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.0014')
        self.limit_order_fee = Decimal('0.0004')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'EUR')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.002', 'BTC')
        self.max_tick_speed = 5
        self.use_cached_orderbook = False

        # TODO: Unclear if these should be configurable or not.
        self.withdrawal_fee = Money('0.001', 'BTC')
        self.btc_credit_limit = Money('0', 'BTC')

        if configuration:
            self.configure(configuration)

    @property
    def pair(self):
        return self.construct_pair(self.currency)

    def req(self, req_method, url, **kwargs):
        req = super(KrakenBTCEURExchange, self).req(req_method, url, **kwargs)

        if not kwargs.get('no_auth'):
            time.sleep(0.1)  # For nonces.

        return req

    def resp(self, req):
        response = super(KrakenBTCEURExchange, self).resp(req)

        if response.get('error'):
            errors_string = str(response['error'])

            if 'Insufficient funds' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Unknown order' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'Invalid nonce' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        try:
            return response['result']
        except KeyError:
            raise exceptions.ExchangeAPIFailureException(self, response)

    def get_trades_info(self, trade_ids):
        req = self.get_trades_info_req(trade_ids)
        return self.get_trades_info_resp(req)

    def get_trades_info_req(self, trade_ids):
        reqs = []

        # /private/QueryTrades only accepts 20 ids at a time.
        for trade_ids_chunk in chunked(trade_ids, 20):
            payload = {
                'txid': ','.join(trade_ids_chunk),
            }

            req = self.req('post', '/private/QueryTrades', data=payload)
            reqs.append(req)

        return reqs

    def get_trades_info_resp(self, reqs):
        result = {}

        for req in reqs:
            result.update(self.resp(req))

        return result

    def get_trades_info_from_ledger(self, trade_ids, order_open_timestamp, order_close_timestamp):
        """
        Check the ledger entries to get accurate numbers for how much our balance was
        changed.

        The ledger is Kraken's only real source of truth, the trades/order endpoints
        lie to us.
        """

        # We add a 0.1s buffer to make sure we get entries right on the boundary
        # timestamps.
        ledger_start = order_open_timestamp - Decimal('0.1')
        # We add a 1s buffer because it takes Kraken a bit of time to write to the
        # ledger.
        ledger_end = order_close_timestamp + Decimal('1')

        entries = self.get_ledger_entries(
            start=ledger_start,
            end=ledger_end,
        )

        trades_info = {}

        for trade_id in trade_ids:
            trades_info[trade_id] = {
                'btc': Money.loads('BTC 0'),
                'btc_fee': Money.loads('BTC 0'),
                'fiat': Money(0, self.currency),
                'fiat_fee': Money(0, self.currency),
            }

        for ledger_id, entry in entries.iteritems():
            trade_id = entry['refid']

            if trade_id not in trade_ids:
                continue

            amount = Decimal(entry['amount'])

            if entry['type'] == 'credit':
                # Credit ledger entries show up when we dip into our line of credit.
                # They have opposite signs, and need to be included along side the
                # trade ledger entries to get accurate trade amounts.
                amount = -amount
            elif entry['type'] == 'trade':
                pass
            else:
                raise exceptions.ExchangeAPIErrorException(
                    self,
                    'Unexpected ledger entry type "%s"' % entry['type'],
                )

            currency = self.convert_from_kraken_currency(entry['asset'])

            if currency == 'BTC':
                trades_info[trade_id]['btc'] += Money(amount, 'BTC')
                trades_info[trade_id]['btc_fee'] += Money(entry['fee'], 'BTC')
            else:
                trades_info[trade_id]['fiat'] += Money(amount, currency)
                trades_info[trade_id]['fiat_fee'] += Money(entry['fee'], currency)

            # There are multiple ledger entries per trade, but they should all be going
            #through at the same time, so we can just take the timestamp of the last
            # one.
            trades_info[trade_id]['time'] = entry['time']

        return trades_info

    def ledger_entry(self, ledger_id):
        req = self.ledger_entry_req(ledger_id)
        return self.ledger_entry_resp(req)

    def ledger_entry_req(self, ledger_id):
        payload = {
            'id': ledger_id,
        }

        return self.req('post', '/private/QueryLedgers', data=payload)

    def ledger_entry_resp(self, req):
        return self.resp(req)

    def get_ledger_entries(self, type=None, start=None, end=None):
        try:
            req = self.get_ledger_entries_req(type, start, end)
            return self.get_ledger_entries_resp(req)
        except LedgerSizeException:
            # If there were too many ledger entries for this time period, split the
            # period in half and run each one seperately.
            # It's a bit of a hack but this is a rare edge case.
            mid = (start + end) / 2
            first_half = self.get_ledger_entries(type, start, mid)
            second_half = self.get_ledger_entries(type, mid, end)

            full_ledger = first_half
            full_ledger.update(second_half)

            return full_ledger

    def get_ledger_entries_req(self, type=None, start=None, end=None):
        payload = {}

        if type:
            payload['type'] = type

        if start:
            payload['start'] = '%.3f' % start

        if end:
            payload['end'] = '%.3f' % end

        return self.req('post', '/private/Ledgers', data=payload)

    def get_ledger_entries_resp(self, req):
        response = self.resp(req)
        count = int(response['count'])

        entries = response['ledger']

        if count > len(entries):
            raise LedgerSizeException('More entries than fit on one page of results')

        return entries

    def closed_orders(self, start=None, end=None, offset=0):
        req = self.closed_orders_req(start, end, offset)
        return self.closed_orders_resp(req)

    def closed_orders_req(self, start=None, end=None, offset=0):
        payload = {}

        if start:
            payload['start'] = start

        if end:
            payload['end'] = end

        if offset:
            payload['ofs'] = str(offset)

        return self.req('post', '/private/ClosedOrders', data=payload)

    def closed_orders_resp(self, req):
        response = self.resp(req)
        count = int(response['count'])
        closed_orders = []

        for order_id, raw_order in response['closed'].iteritems():
            raw_order['order_id'] = order_id
            closed_orders.append(raw_order)

        return count, closed_orders

    ######## Common Exchange Methods ########

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('KRAKEN_BTC_EUR_API_KEY')
            self.secret = self._load_env('KRAKEN_BTC_EUR_API_SECRET')

    def auth_request(self, req_method, url, request_args):
        """
        This modifies the request_args.
        """
        self.load_creds()

        endpoint = url.replace(self.base_url, '')
        endpoint = '/0' + endpoint

        nonce = unicode(int(round(time.time() * 1000)))

        try:
            payload = request_args['data']
        except KeyError:
            payload = request_args['data'] = {}

        payload.update({
            'nonce': nonce,
        })

        post_data = urllib.urlencode(payload)
        message = endpoint + hashlib.sha256(nonce + post_data).digest()
        sig = base64.b64encode(hmac.new(base64.b64decode(self.secret), message, hashlib.sha512).digest())

        try:
            headers = request_args['headers']
        except KeyError:
            headers = request_args['headers'] = {}

        headers.update({
            'API-Key': self.api_key,
            'API-Sign': sig,
        })

    def get_balance_req(self):
        return self.req('post', '/private/BalanceEx')

    def get_balance_resp(self, req):
        response = self.resp(req)

        total_balance = Balance()

        # We only want to load the balances for the pair we trade on this account
        # (BTC + self.currency).  For example we have a small USD balance in our main
        # EUR Kraken account which we want to ignore. Including it in the balance breaks
        # some other parts of our system which expect to only find a single fiat
        # currency.
        supported_currencies = ['BTC', self.currency]

        for currency in supported_currencies:
            kraken_currency = self.convert_to_kraken_currency(currency)

            balance_amount = Decimal(response[kraken_currency]['balance'])
            credit_amount = Decimal(response[kraken_currency].get('credit_used', 0))

            balance = Money(balance_amount, currency)
            credit = Money(credit_amount, currency)

            total_balance += (balance - credit)

        return total_balance

    def get_ticker_req(self, verify=True):
        url = '/public/Ticker?pair=%s' % self.pair
        return self.req('get', url, no_auth=True, verify=verify)

    def get_ticker_resp(self, req):
        response = self.resp(req)
        ticker = response[self.pair]

        return {
            'high': Money(ticker['h'][1], self.currency),
            'low': Money(ticker['l'][1], self.currency),
            'last': Money(ticker['c'][0], self.currency),
            'volume': Money(ticker['v'][1], 'BTC'),
        }

    def _get_orderbook_from_api_req(self, verify=True):
        url = '/public/Depth?pair=%s&count=%s' % (self.pair, self.orderbook_depth)
        return self.req('get', url, no_auth=True, verify=verify)

    def _get_raw_bids(self, raw_orderbook):
        return raw_orderbook[self.pair]['bids']

    def _get_raw_asks(self, raw_orderbook):
        return raw_orderbook[self.pair]['asks']

    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        mode = self._order_mode_from_const(mode)

        try:
            payload = {
                'pair': self.pair,
                'type': mode,
                'ordertype': 'limit',
                'price': unicode(price.amount),
                'volume': unicode(volume.amount),
            }

        except AttributeError:
            raise TypeError('volume and price must be Money objects')

        return self.req('post', '/private/AddOrder', data=payload)

    def place_order_resp(self, req):
        response = self.resp(req)

        try:
            return {'success': True, 'order_id': unicode(response['txid'][0])}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order_id',
            )

    def get_open_orders_req(self):
        payload = {}
        return self.req('post', '/private/OpenOrders', data=payload)

    def get_open_orders_resp(self, req):
        response = self.resp(req)
        open_orders = []

        try:
            raw_open_orders = response['open']

            for order_id, raw_order in raw_open_orders.iteritems():
                if raw_order['status'] == 'open':
                    mode = self._order_mode_to_const(raw_order['descr']['type'])
                    volume = Money(raw_order['vol'], 'BTC')
                    volume_executed = Money(raw_order['vol_exec'], 'BTC')
                    price = Money(raw_order['descr']['price'], self.currency)

                    order = {
                        'mode': mode,
                        'id': order_id,
                        'price': price,
                        'volume_remaining': volume - volume_executed,
                    }

                    open_orders.append(order)
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'Open orders format incorrect',
            )

        return open_orders

    def get_order_details(self, order_id):
        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req, order_id)

    def get_order_details_req(self, order_id):
        return self.get_multi_order_details_req([order_id])

    def get_order_details_resp(self, req, order_id):
        return self.get_multi_order_details_resp(req, [order_id])[order_id]
            
    def get_multi_order_details(self, order_ids):
        req = self.get_multi_order_details_req(order_ids)
        return self.get_multi_order_details_resp(req, order_ids)
 
    def get_multi_order_details_req(self, order_ids):
        order_ids = [unicode(o) for o in order_ids]

        payload = {
            'trades': True,
            'txid': ','.join(order_ids),
        }

        return self.req('post', '/private/QueryOrders', data=payload)

    def get_multi_order_details_resp(self, req, order_ids):
        multi_trades = self.resp(req)
        data = {}

        for order_id in order_ids:
            total_fiat = Money('0', self.currency)
            total_btc = Money('0', 'BTC')
            our_trades = []

            if order_id in multi_trades:
                order = multi_trades[order_id]
                trade_ids = order.get('trades', [])

                if trade_ids:
                    opentm = order['opentm']

                    # Partially-executed orders haven't "closed" yet so they don't
                    # have a closetm. We only need the already executed trades, so we
                    # end the interval at NOW().
                    if 'closetm' in order:
                        closetm = order['closetm']
                    else:
                        closetm = Decimal(Delorean().epoch)

                    trades = self.get_trades_info_from_ledger(
                        trade_ids,
                        opentm,
                        closetm,
                    )

                    for t_id, t in trades.iteritems():
                        fiat = abs(t['fiat'])
                        btc = abs(t['btc'])

                        if t['btc_fee'] and t['fiat_fee']:
                            raise exceptions.ExchangeAPIErrorException(
                                self,
                                '#%s charged fees in both fiat (%s) and BTC (%s)' % (
                                order_id,
                                t['fiat_fee'],
                                t['btc_fee'],
                            ))
                        elif t['btc_fee']:
                            fee = t['btc_fee']
                        else:
                            fee = t['fiat_fee']

                        total_fiat += fiat
                        total_btc += btc

                        our_trades.append({
                            'time': int(t['time']),
                            'trade_id': unicode(t_id),
                            'fee': fee,
                            'btc': btc,
                            'fiat': fiat,
                        })

            data[order_id] = {
                'time_created': int(order['opentm']),
                'type': self._order_mode_to_const(order['descr']['type']),
                'btc_total': total_btc,
                'fiat_total': total_fiat,
                'trades': our_trades,
            }

        return data

    def cancel_order_req(self, order_id):
        payload = {
            'txid': unicode(order_id),
        }

        return self.req('post', '/private/CancelOrder', data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)

        if response.get('count', 0) > 0:
            return {'success': True}
        else:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'cancelled count should be > 0',
            )

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if self.volume_currency != 'BTC':
            raise TypeError('Kraken withdrawals are only supported for BTC right now.')

        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        # The Kraken API only takes names which are mapped to address. The mapping can
        # be adjusted here: https://www.kraken.com/u/funding/withdraw?asset=XXBT
        # Since our system passes around addresses, we search through the ENV vars to
        # find the corresponding exchange name, which we then pass to Kraken.
        deposit_addresses = {
            name: addr
            for name, addr in os.environ.iteritems() if '_DEPOSIT_ADDRESS' in name
        }

        address_to_name_map = {
            addr: name.replace('_DEPOSIT_ADDRESS', '')
            for name, addr in deposit_addresses.iteritems()
        }

        try:
            destination_exchange_name = address_to_name_map[address]
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'Could not find matching exchange for %s' % address,
            )

        volume += self.withdrawal_fee

        payload = {
            'asset': 'XXBT',
            'key': destination_exchange_name,
            'amount': volume.amount,
        }

        return self.req('post', '/private/Withdraw', data=payload)

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)
        return response

    def get_order_audit_data(self, skip_recent=0, lookback_hours=2):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (including
        only orders that have some trades).
        """
        raw_orders = []
        start = Delorean().last_hour(lookback_hours).epoch

        offset = 0
        count, raw_chunk = self.closed_orders(start)
        raw_orders += raw_chunk
        offset += len(raw_chunk)

        while offset < count:
            logger.info('%s orders fetched, %s remaining' % (offset, count - offset))
            _, raw_chunk = self.closed_orders(start, offset=offset)
            raw_orders += raw_chunk
            offset += len(raw_chunk)

        raw_orders = raw_orders[skip_recent:]

        orders = OrderedDict()

        for raw_order in raw_orders:
            volume_executed = Money(raw_order['vol_exec'], 'BTC')

            if volume_executed > 0:
                order_id = raw_order['order_id']
                orders[order_id] = volume_executed

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        return Money('5', 'EUR')

    @classmethod
    def construct_pair(cls, fiat_currency):
        btc_currency_code = cls.convert_to_kraken_currency('BTC')
        fiat_currency_code = cls.convert_to_kraken_currency(fiat_currency)

        return btc_currency_code + fiat_currency_code

    @classmethod
    def convert_from_kraken_currency(cls, kraken_currency):
        if kraken_currency == 'XXBT':
            currency = 'BTC'
        elif kraken_currency[0] == 'Z':
            currency = kraken_currency[1:]

        if currency not in Money.CURRENCIES:
            raise ValueError('invalid currency value: \'%s\'' % currency)

        return currency

    @classmethod
    def convert_to_kraken_currency(cls, currency):
        if currency == 'BTC':
            kraken_currency = 'XXBT'
        else:
            kraken_currency = 'Z' + currency

        return kraken_currency
