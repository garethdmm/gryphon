# -*- coding: utf-8 -*-
from collections import OrderedDict
import hashlib

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


class OKCoinBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(OKCoinBTCUSDExchange, self).__init__(session)

        self.name = u'OKCOIN_BTC_USD'
        self.friendly_name = u'OKCoin BTC-USD'
        self.currency = u'USD'
        self.volume_currency = 'BTC'
        self.base_url = 'https://www.okcoin.com/api/v1'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        # Codes, accurate for requests but not for responses. Responses number
        # -1 through 2.
        self.PARAM_ORDER_STATUS_UNFILLED = 0
        self.PARAM_ORDER_STATUS_FILLED = 1

        # Codes these are the statuses that the endpoints give back.
        self.ORDER_STATUS_CANCELLED = -1
        self.ORDER_STATUS_OPEN = 0
        self.ORDER_STATUS_PARTIALLY_FILLED = 1
        self.ORDER_STATUS_FULLY_FILLED = 2

        self.errors = {
            10000: 'Required field, can not be null',
            10001: 'Request frequency too high',
            10002: 'System error',
            10003: 'Not in reqest list, please try again later',
            10004: 'IP not allowed to access the resource',
            10005: '\'secretKey\' does not exist',
            10006: '\'partner\' does not exist',
            10007: 'Signature does not match',
            10008: 'Illegal parameter',
            10009: 'Order does not exist',
            10010: 'Insufficient funds',
            10011: 'Amount too low',
            10012: 'Only btc_usd ltc_usd supported',
            10013: 'Only support https request',
            10014: 'Order price must be between 0 and 1,000,000',
            10015: 'Order price differs from current market price too much',
            10016: 'Insufficient coins balance',
            10017: 'API authorization error',
            10026: 'Loan (including reserved loan) and margin cannot be withdrawn',
            10027: 'Cannot withdraw within 24 hrs of authentication information modification',
            10028: 'Withdrawal amount exceeds daily limit',
            10029: 'Account has unpaid loan, please cancel/pay off the loan before withdraw',
            10031: 'Deposits can only be withdrawn after 6 confirmations',
            10032: 'Please enabled phone/google authenticator',
            10033: 'Fee higher than maximum network transaction fee',
            10034: 'Fee lower than minimum network transaction fee',
            10035: 'Insufficient BTC/LTC',
            10036: 'Withdrawal amount too low',
            10037: 'Trade password not set',
            10040: 'Withdrawal cancellation fails',
            10041: 'Withdrawal address not approved',
            10042: 'Admin password error',
            10100: 'User account frozen',
        }

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.001')
        self.limit_order_fee = Decimal('0.002')
        self.fee = self.market_order_fee
        self.withdrawal_fee = Money('0.001', 'BTC')
        self.use_cached_orderbook = False
        self.max_tick_speed = 1

        if configuration:
            self.configure(configuration)

    def resp(self, req):
        response = super(OKCoinBTCUSDExchange, self).resp(req)

        error_code = response.get('error_code', None)

        if error_code:
            if error_code == 10009:
                raise exceptions.CancelOrderNotFoundError()
            elif error_code in [10016, 10010]:
                raise exceptions.InsufficientFundsError()
            else:
                raise exceptions.ExchangeAPIErrorException(
                    self,
                    self.errors[error_code],
                )

        return response

    def round(self, m):
        if m.currency == 'USD':
            return m.round_to_decimal_places(
                4,
                rounding=cdecimal.ROUND_HALF_EVEN,
            )
        elif m.currency == 'BTC':
            return m.round_to_decimal_places(
                8,
                rounding=cdecimal.ROUND_HALF_EVEN,
            )

    def ticker_req(self, verify=True):
        return self.req('get', '/ticker.do', no_auth=True, verify=verify)


    def ticker_resp(self, req):
        response = self.resp(req)

        response = response['ticker']

        return {
            'high': Money(response['high'], 'USD'),
            'low': Money(response['low'], 'USD'),
            'last': Money(response['last'], 'USD'),
            'bid': Money(response['buy'], 'USD'),
            'ask': Money(response['sell'], 'USD'),
            'volume': Money(response['vol'], 'BTC')
        }


    def all_transactions(self, page=0, unfilled_orders=None):
        req = self.all_transactions_req(
            page=page, 
            unfilled_orders=unfilled_orders
        )

        return self.all_transactions_resp(req)


    def all_transactions_req(self, page=0, unfilled_orders=None):
        # The unfilled orders parameter allows us to query for filled orders with
        # status=1 and unfilled orders with status=0.

        status = (self.PARAM_ORDER_STATUS_UNFILLED if unfilled_orders
                      else self.PARAM_ORDER_STATUS_FILLED)

        payload = {
            'symbol': 'btc_usd',
            'status': status,
            'current_page': page,
            'page_length': 200,
        }

        return self.req('post', '/order_history.do', data=payload)

    def all_transactions_resp(self, req):
        return self.resp(req)

    ###### Common Exchange Methods ######

    def load_creds(self):
        try:
            self.api_key
            self.secret
            self.partner_id
        except AttributeError:
            self.api_key = self._load_env('OKCOIN_BTC_USD_API_KEY')
            self.secret = self._load_env('OKCOIN_BTC_USD_API_SECRET')
            self.partner_id = self._load_env('OKCOIN_BTC_USD_PARTNER_ID')

    def auth_request(self, req_method, url, request_args):
        self.load_creds()

        try:
            payload = request_args['data']
        except KeyError:
            payload = request_args['data'] = {}
       
        payload.update({
            'api_key': self.api_key,
        })

        signature = self.get_okcoin_signature(payload, self.secret),

        payload.update({
            'sign': signature[0],
        })

    def get_okcoin_signature(self, params, secretKey):
        """
        Helper function, written by OKCoin, for building the auth signature.
        """
        sign = ''

        for key in sorted(params.keys()):
            sign += key + '=' + str(params[key]) + '&'

        return hashlib.md5(sign + 'secret_key=' + secretKey).hexdigest().upper()


    def balance_req(self):
        return self.req('post', '/userinfo.do')


    def balance_resp(self, req):
        response = self.resp(req)

        try:
            balances = response['info']['funds']

            btc_available = Money(balances['free']['btc'], 'BTC')
            usd_available = Money(balances['free']['usd'], 'USD')
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'Balance missing expected keys',
            )

        balance = Balance()
        balance['BTC'] = btc_available
        balance['USD'] = usd_available

        return balance

    def _get_order_book_req(self, verify=True):
        return self.req('get', '/depth.do', no_auth=True, verify=verify)
            
    def create_trade_req(self, mode, volume, price, is_market_order=False):
        volume = self.round(volume)
        price = self.round(price)

        trade_type = self.from_const(mode)

        try:
            payload = {
                'symbol': 'btc_usd',
                'type': trade_type,
                'amount': volume.amount,
                'price': price.amount,
            }

        except AttributeError:
            raise TypeError('volume and price must be Money objects')

        return self.req('post', '/trade.do', data=payload)

    def create_trade_resp(self, req):
        response = self.resp(req)

        try:
            return {
                'success': True, 
                'order_id': str(response['order_id'])
            }

        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order id',
            )


    def order_fee(self, order_id):
        req = self.order_fee_req(order_id)
        return self.order_fee_resp(req)

    def order_fee_req(self, order_id):
        payload = {
            'order_id': order_id,
            'symbol': 'btc_usd',
        }

        return self.req('post', '/order_fee.do', data=payload)

    def order_fee_resp(self, req):
        try:
            response = self.resp(req)
        except CancelOrderNotFoundError:
            # OkCoin has started returning this error on non-executed orders or orders
            # with no fees.
            return Money('0', 'USD')

        # Okcoin returns fees as negative values.
        fee_amount = abs(Decimal(response['data']['fee']))
        fee_currency = 'USD'

        # If the order has not been filled, response['data']['type] is not
        # in the response.
        if 'type' in response['data']:
            fee_currency = response['data']['type'].upper()

        fee = Money(fee_amount, fee_currency)

        return fee

    def open_orders_req(self):
        """
        This implementation assumes that no open orders were placed more than a week
        ago.
        """
        return self.all_transactions_req(page=0, unfilled_orders=True)

    def open_orders_resp(self, req):
        response = self.resp(req)

        raw_open_orders = response['orders']
        open_orders = []

        for raw_order in raw_open_orders:
            mode = self._order_mode_to_const(raw_order['type'])

            usd_price = Money(raw_order['price'], 'USD')
            volume = Money(raw_order['amount'], 'BTC')
            volume_filled = Money(raw_order['deal_amount'], 'BTC')
            remaining = volume - volume_filled

            order = {
                'mode': mode,
                'id': str(raw_order['order_id']),
                'price': usd_price,
                'volume_remaining': remaining
            }

            open_orders.append(order)

        return open_orders

    def order_details(self, order_id):
        reqs = self.order_details_req(order_id)
        return self.order_details_resp(reqs)

    def order_details_req(self, order_id):
        payload = {
            'symbol': 'btc_usd',
            'order_id': order_id,
        }

        reqs = {
            'details': self.req('post', '/order_info.do', data=payload),
            'fee': self.order_fee_req(order_id),
        }

        return reqs

    def order_details_resp(self, reqs):
        details_response = self.resp(reqs['details'])
        fee = self.order_fee_resp(reqs['fee'])

        if details_response['orders']:
            raw_order = details_response['orders'][0]
            order = self.parse_raw_order(raw_order, fee)

            return order
        else:
            empty_order = {
                'time_created': None,
                'type': None,
                'btc_total': Money(0, 'BTC'),
                'fiat_total': Money(0, 'USD'),
                'trades': [],
            }

            return empty_order

    def multi_order_details_req(self, order_ids):
        order_ids_string = ','.join(order_ids)
        details_reqs = []
        fee_reqs = {}

        filled_payload = {
            'symbol': 'btc_usd',
            # we only query for filled orders because this endpoint
            # is used for after-filling accounting
            # okcoin docs say this should be 2 but they're wrong
            'type': self.PARAM_ORDER_STATUS_FILLED,
            'order_id': order_ids_string,
        }

        details_reqs.append(self.req('post', '/orders_info.do', data=filled_payload))

        unfilled_payload = {
            'symbol': 'btc_usd',
            # we only query for filled orders because this endpoint
            # is used for after-filling accounting
            # okcoin docs say this should be 1 but they're wrong
            'type': self.PARAM_ORDER_STATUS_UNFILLED,
            'order_id': order_ids_string,
        }

        details_reqs.append(self.req('post', '/orders_info.do', data=unfilled_payload))

        for order_id in order_ids:
            fee_reqs[order_id] = self.order_fee_req(order_id)

        reqs = {
            'details': details_reqs,
            'fees': fee_reqs,
        }

        return reqs

    def multi_order_details_resp(self, reqs, order_ids_not_used):
        raw_orders = []
        fees = {}

        for req in reqs['details']:
            response = self.resp(req)
            raw_orders += response['orders']

        for order_id, req in reqs['fees'].items():
            response = self.order_fee_resp(req)
            fees[order_id] = response
            
        data = {}

        for raw_order in raw_orders:
            order_id = str(raw_order['order_id'])
            order = self.parse_raw_order(raw_order, fees[order_id])

            data[order_id] = order

        return data

    def parse_raw_order(self, raw_order, fee):
        mode = self._order_mode_to_const(raw_order['type'])
 
        timestamp = int(float(raw_order['create_date'])) / 1000

        btc_total = Money(raw_order['deal_amount'], 'BTC')
        avg_price = Money(raw_order['avg_price'], 'USD')

        total_usd = self.round(avg_price * btc_total.amount)

        # okcoin does not have seperate notions of trade and raw_order
        # so if we see a partially filled raw_order here, treat it as a 
        # full trade

        trades = []

        if total_usd > 0:
            fake_trade = {
                'time': timestamp,
                'trade_id': None,
                'fee': fee,
                'btc': btc_total,
                'fiat': total_usd,
            } 

            trades.append(fake_trade)

        order = {
            'time_created': timestamp,
            'type': mode,
            'btc_total': btc_total,
            'fiat_total': total_usd,
            'trades': trades
        }


        return order

    def cancel_order_req(self, order_id):
        payload = { 
            'symbol': 'btc_usd',
            'order_id': order_id,
        }

        return self.req('post', '/cancel_order.do', data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)
        return {'success': True}

    def withdraw_crypto_req(self, address, volume):
        if not isinstance(address, basestring):
            raise TypeError('Withdrawal address must be a string')

        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        admin_password = self._load_env('OKCOIN_BTC_USD_ADMIN_PASSWORD')

        payload = {
            'symbol': 'btc_usd',
            'chargefee': '0.001', # generous miner fee, 30 cents
            'trade_pwd': admin_password,
            'withdraw_address': address,
            'withdraw_amount': str(volume.amount),
        }

        return self.req('post', '/withdraw.do', data=payload)

    def withdraw_crypto_resp(self, req):
        response = self.resp(req)
        return {'success': True, 'exchange_withdrawal_id': response['withdraw_id']}

    def process_db_balance_for_audit(self, db_balance):
        # OkCoin truncates to 6 decimal places in their API, so we want do the same
        # to our stored balance before comparing them.
        if db_balance.currency == 'BTC':
            db_balance = db_balance.round_to_decimal_places(6, cdecimal.ROUND_HALF_EVEN)

        return db_balance

    def audit(self, skip_recent=0):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (only include
        orders that have some trades).
        """
        all_orders = self.all_transactions(unfilled_orders=False)
        all_orders = all_orders['orders']

        # list of 100ish previous orders with volume filled > 0
        orders = OrderedDict()

        for order in all_orders:
            order_id = str(order['order_id'])
            status = order['status']
            volume_filled = Money(order['deal_amount'], 'BTC')

            if (status == self.ORDER_STATUS_PARTIALLY_FILLED 
                    or status == self.ORDER_STATUS_FULLY_FILLED):
                orders[order_id] = volume_filled

        return orders

