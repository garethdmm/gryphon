# -*- coding: utf-8 -*-
import time
import os
import datetime
import hmac
import hashlib

from cdecimal import *
from delorean import Delorean
from collections import OrderedDict, defaultdict

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class QuadrigaBTCCADExchange(ExchangeAPIWrapper):
    """
    Test Order ID (should be cancelled):
        c11tajt6k7ilo4oasjgodzpb0u28y4nb5o5g8ymt65eu9352mmq0lfbl9du8hhkn
    """

    def __init__(self, session=None, configuration=None):
        super(QuadrigaBTCCADExchange, self).__init__(session)

        self.name = u'QUADRIGA_BTC_CAD'
        self.friendly_name = u'Quadriga CX BTC-CAD'
        self.base_url = 'https://api.quadrigacx.com/v2'
        self.currency = u'CAD'
        self.volume_currency = u'BTC'
        self.bid_string = '0'
        self.ask_string = '1'

        # Configurables with defaults.
        self.fee = Decimal('0.0025')
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.fiat_balance_tolerance = Money('0.0001', 'CAD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.0025', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def req(self, req_method, url, **kwargs):
        req = super(QuadrigaBTCCADExchange, self).req(req_method, url, **kwargs)
        time.sleep(0.2) # Unfortunately necessary due to nonce errors.

        return req

    def resp(self, req):
        response = super(QuadrigaBTCCADExchange, self).resp(req)

        try:
            if 'error' in response:
                errors_string = response['error']['message']

                if 'exceeds available' in errors_string:
                    raise exceptions.InsufficientFundsError()
                elif 'Cannot perform request - not found' in errors_string:
                    raise exceptions.CancelOrderNotFoundError()
                elif 'Nonce' in errors_string:
                    raise exceptions.NonceError()
                else:
                    logger.info(response['error'])
                    raise exceptions.ExchangeAPIErrorException(self, errors_string)

            return response
        except KeyError:
            raise exceptions.ExchangeAPIFailureException(self, response)

    def transactions_req(self):
        payload = {
            'limit': 100,
        }

        return self.req('post', '/user_transactions', data=payload)
    
    def transactions_resp(self, req):
        return self.resp(req)
        
    def transactions(self):
        return self.transactions_resp(self.transactions_req()) 
    
    def trades(self):
        raw_transactions =  self.transactions()
        trades = []

        for raw_transaction in raw_transactions:
            # It is a trade if an order_id is present in the transaction.
            if int(raw_transaction['type']) == 2:
                btc = Money(raw_transaction['btc'], 'BTC')
                fiat = Money(raw_transaction[self.currency.lower()], self.currency)

                # Bids look like this: {'cad':'-5075.50','btc':'15.77622250'}
                # and asks like this:  {'cad':'256.88','btc':'-0.80000000'}
                if btc > 0: # Bid
                    # Bids have BTC fees
                    fee = Money(raw_transaction['fee'], 'BTC')
                    # Quadriga returns amounts which have fees removed
                    # we need to add them back in to keep our accounting accurate
                    btc += fee

                    if fiat > 0:
                        raise exceptions.ExchangeAPIErrorException(
                            self,
                            'Trade #%s does not have opposite btc and fiat signs' % (
                            raw_transaction['id'],
                        ))

                    fiat = abs(fiat)
                elif btc < 0:  # Ask.
                    # Asks have CAD fees.
                    fee = Money(raw_transaction['fee'], self.currency)
                    fiat += fee

                    if fiat < 0:
                        raise exceptions.ExchangeAPIErrorException(
                            self,
                            'Trade #%s does not have opposite btc and fiat signs' % (
                            raw_transaction['id'],
                        ))

                    btc = abs(btc)
                else:
                    raise exceptions.ExchangeAPIErrorException(
                        self,
                        'Zero volume Trade #%s, so API doesn\'t tell us the side.' % ( 
                        raw_transaction['id'],
                    ))

                trades.append({
                    'time': self._datetime_to_timestamp(raw_transaction['datetime']),
                    'trade_id': unicode(raw_transaction['id']),
                    'order_id': unicode(raw_transaction['order_id']),
                    'btc': btc,
                    'fiat': fiat,
                    'fee': fee,
                })

        return trades
    
    def trades_for_order(self, order_id):
        trades = self.trades()
        return [t for t in trades if t['order_id'] == order_id]

    def _datetime_to_timestamp(self, dt_string):
        # As of 2015-12-01 13:00 UTC, quadriga timestamps are now in UTC
        # (with no warning or backwards compatability, of course)
        return int(parse(dt_string).epoch)

    ######## Common Exchange Methods ########

    # modifies request_args
    def auth_request(self, req_method, url, request_args):
        try:
            self.api_key
            self.secret
            self.client_id
        except AttributeError:
            self.api_key = self._load_env('QUADRIGA_BTC_CAD_KEY')
            self.client_id = self._load_env('QUADRIGA_BTC_CAD_CLIENT_ID')
            self.secret = self._load_env('QUADRIGA_BTC_CAD_SECRET')

        try:
            payload = request_args['data']
        except KeyError:
            payload = request_args['data'] = {}

        nonce = unicode(int(round(time.time() * 1000)))
        message= nonce + self.api_key + self.client_id

        sig = hmac.new(
            hashlib.md5(self.secret).hexdigest(),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest().upper()

        payload.update({
            'nonce':nonce,
            'key': self.api_key,
            'signature':sig
        })
        
    def get_balance_req(self):
        return self.req('post', '/balance')

    def get_balance_resp(self, req):
        response = self.resp(req)

        try:
            btc_balance = Money(response['btc_balance'], 'BTC')
            cad_balance = Money(response['cad_balance'], 'CAD')
        except KeyError:
            raise exceptions.ExchangeAPIFailureException(self, response)

        data = Balance()
        data['BTC'] = btc_balance
        data['CAD'] = cad_balance

        return data
        
    def _get_orderbook_from_api_req(self, verify=True):
        return self.req('get', '/order_book', no_auth=True, verify=verify)
    
    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        payload = {
            'amount': '%.8f' % volume.amount,
            'price': '%.2f' % price.amount,
        }

        if mode == Consts.BID:
            return self.req('post', '/buy', data=payload)
        elif mode == Consts.ASK:
            return self.req('post', '/sell', data=payload)
        else:
            raise ValueError('Mode must be either bid_string or the ask_string.')

    def place_order_resp(self, req):
        response = self.resp(req)

        try:
            return {'success': True, 'order_id': unicode(response['id'])}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order_id. Response: %s' % response,
            )
    
    def get_open_orders_req(self):
        return self.req('post', '/open_orders')
        
    def get_open_orders_resp(self, req):
        raw_open_orders = self.resp(req)
        raw_open_orders = raw_open_orders if raw_open_orders else []
        open_orders = []

        for raw_order in raw_open_orders:
            mode = self._order_mode_to_const(str(raw_order['type']))

            order = {
                'mode': mode,
                'id': str(raw_order['id']),
                'price': Money(raw_order['price'], 'CAD'),
                'volume_remaining': Money(raw_order['amount'], 'BTC'),
            }

            open_orders.append(order)

        return open_orders

    def get_order_details(self, order_id):
        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req)
    
    def get_order_details_req(self, order_id):
        payload = {
            'id': unicode(order_id),
        }

        return self.req('post', '/lookup_order', data=payload)
    
    def get_order_details_resp(self, req):
        order = self.resp(req)

        try:
            order = order[0]
        except KeyError as e:
            ExchangeAPIErrorException(self, 'malformed response: %s' % order)
            
        trades = self.trades_for_order(order['id'])
        time_created = self._datetime_to_timestamp(order['created'])
        mode = self._order_mode_to_const(str(order['type']))

        result = {
            'time_created': time_created,
            'type': mode,
            'btc_total': sum([t['btc'] for t in trades], Money('0', 'BTC')),
            'fiat_total': sum([t['fiat'] for t in trades], Money('0', self.currency)),
            'trades': trades,
        }

        return result
    
    def get_multi_order_details_req(self, order_ids):
        data = {}

        for oid in order_ids:
            data[oid] = self.get_order_details_req(oid)

        return data
    
    def get_multi_order_details_resp(self, reqs):
        data = {}

        for oid in reqs:
            data[oid] = self.get_order_details_resp(reqs[oid])

        return data

    def get_ticker_req(self, verify=True):
        return self.req('get', '/ticker', no_auth=True, verify=verify)
    
    def get_ticker_resp(self, req):
        response = self.resp(req)

        return {
            'high': Money(response['high'], 'CAD'),
            'low': Money(response['low'], 'CAD'),
            'last': Money(response['last'], 'CAD'),
            'volume': Money(response['volume'], 'BTC'),
        }
    
    def cancel_order_req(self, order_id):
        payload = {
            'id': order_id,
        }

        return self.req('post', '/cancel_order', data=payload)
    
    def cancel_order_resp(self, req):
        response = self.resp(req)
        return {'success': True}

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        payload = {
            'amount': volume.amount,
            'address': address,
        }

        return self.req('post', '/bitcoin_withdrawal', data=payload)

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)
        return {'success': True}

    def get_order_audit_data(self, skip_recent=0):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (only include 
        orders that have some trades)
        """        
        orders = OrderedDict()
        trades_to_audit = self.trades()
        
        # Trades from the same order aren't guaranteed to be next to each other, so we
        # need to group them.
        trades_to_audit.sort(key=lambda t:(t['time']), reverse=True)

        for trade in trades_to_audit:
            order_id = str(trade['order_id'])
            try:
                orders[order_id] += abs(trade['btc'])
            except KeyError:
                orders[order_id] = abs(trade['btc'])

        # Remove the oldest 2 orders, because its trades might be wrapped around a page 
        # gap this would give us an innacurate volume_filled number. We need to remove
        # 2 because there could be an ask and a bid
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

