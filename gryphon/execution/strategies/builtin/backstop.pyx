"""
This sub-strategy gives code to maintain backstop orders in a market making algorithm
far back of the midpoint (e.g., 10% back of the midpoint) in order to catch black swan
swings that we can use for arbitrage or simply to open positions at very favourable
prices.
"""

from datetime import datetime, timedelta

from cdecimal import *
import termcolor as tc

from gryphon.execution.strategies.base import Strategy
from gryphon.lib.exchange.base import Exchange
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exceptions import *
from gryphon.lib.models.datum import Datum
from gryphon.lib.models.event import EventRecorder
from gryphon.lib.money import *
from gryphon.lib.session import get_a_redis_connection


ABSOLUTE_MAX_ORDER_VOLUME = Money('128', "BTC")
PREDICTIVE_VOLUME_REDIS_KEY = 'ML_PREDICTION'


class BackstopOrdersStrategy(Strategy):
    def should_use_backstop_orders(self):
        backstops_enabled = self.config.get('use_backstop_orders', 'no') == 'yes'

        can_place_orders = (
            self.has_required_balance_for_backstop_bid()
            or self.has_required_balance_for_backstop_ask()
        )

        if backstops_enabled and can_place_orders:
            return True
        else:
            return False

    def has_required_balance_for_backstop_bid(self):
        """
        We require enough fiat balance to place a 64 bitcoin buy order and a 10 bitcoin
        backstop in order still be placing backstop orders.
        """

        max_bids_total_volume = (
            self.config['max_position'] + self.config['backstop_volume']
        )

        required_balance = max_bids_total_volume.amount * self.fundamental_value

        if self.exchange_data.balance[self.exchange.currency] > required_balance:
            return True
        else:
            return False

    def has_required_balance_for_backstop_ask(self):
        """
        We require enough bitcoin balance to place a 64 bitcoin sell order and a 10
        bitcoin backstop in order still be placing backstop orders.
        """

        required_balance = self.config['max_position'] + self.config['backstop_volume']

        if self.exchange_data.balance['BTC'] > required_balance:
            return True
        else:
            return False

    def current_backstop_bid_and_ask(self, current_orders):
        try:
            bids = [
                o for o in current_orders
                if o['mode'] == Consts.BID and o['is_backstop']== True
            ]

            assert len(bids) <= 1

            bid = bids[0]
        except IndexError:
            bid = None

        try:
            asks = [
                o for o in current_orders
                if o['mode'] == Consts.ASK and o['is_backstop'] == True
            ]

            assert len(asks) <= 1

            ask = asks[0]
        except IndexError:
            ask = None

        return bid, ask

    def current_core_bid_and_ask(self, current_orders):
        try:
            bids = [
                o for o in current_orders
                if o['mode'] == Consts.BID and o['is_backstop'] == False
            ]

            assert len(bids) <= 1

            bid = bids[0]
        except IndexError:
            bid = None

        try:
            asks = [
                o for o in current_orders
                if o['mode'] == Consts.ASK and o['is_backstop'] == False
            ]

            assert len(asks) <= 1

            ask = asks[0]
        except IndexError:
            ask = None

        return (bid, ask)

    def calculate_backstop_volumes(self):
        """
        The current sizing logic for backstops is to have a fixed size order if we
        pass the has_required_required_balance checks and zero otherwise.
        """
        backstop_bid_volume = Money('0', 'BTC')
        backstop_ask_volume = Money('0', 'BTC')

        if self.has_required_balance_for_backstop_bid():
            backstop_bid_volume = self.config['backstop_volume']

        if self.has_required_balance_for_backstop_ask():
            backstop_ask_volume = self.config['backstop_volume']

        return backstop_bid_volume, backstop_ask_volume

    def calculate_backstop_prices(self, core_bid_price, core_ask_price):
        backstop_ask_price = core_ask_price + self.config['backstop_price_level']
        backstop_bid_price = core_bid_price - self.config['backstop_price_level']

        return backstop_bid_price, backstop_ask_price

    def backstop_datums(self):
        return [Datum('BACKSTOP')]

    def cancel_all_backstop_orders(self, current_orders):
        current_bid, current_ask = self.current_backstop_bid_and_ask(current_orders)

        if current_bid:
            self.harness.cancel_order(current_bid['id'])

        if current_ask:
            self.harness.cancel_order(current_ask['id'])

        return

    def update_backstop_orders(self, core_bid_price, core_ask_price, orderbook, current_orders):
        """
        Set a pair of orders far back back on either side of the fundamental value in
        order to catch a very fast swing.
        """

        if not self.should_use_backstop_orders():
            self.cancel_all_backstop_orders(current_orders)
            return

        current_bid, current_ask = self.current_backstop_bid_and_ask(current_orders)

        # Cancel any existing backstop bid if we've just moved into a state where
        # has_required_balance no longer passes.
        if not self.has_required_balance_for_backstop_bid():
            if current_bid:
                self.harness.cancel_order(current_bid['id'])

        # Likewise for asks.
        if not self.has_required_balance_for_backstop_ask():
            if current_ask:
                self.harness.cancel_order(current_ask['id'])

        backstop_bid_volume, backstop_ask_volume = self.calculate_backstop_volumes()

        backstop_bid_price, backstop_ask_price = self.calculate_backstop_prices(
            core_bid_price,
            core_ask_price,
        )

        backstop_datums = self.backstop_datums()

        if self.config.get('buy', 'yes') != 'no':
            try:
                if not current_bid:
                    self.log(
                        'Placing new Backstop_bid: %s at %s',
                        (backstop_bid_volume, backstop_bid_price),
                    )

                    self.harness.order(
                        Consts.BID,
                        backstop_bid_volume,
                        backstop_bid_price,
                        orderbook=orderbook,
                        datums=backstop_datums,
                    )

                else:
                    current_bid_price = current_bid['price']

                    if self.are_different_enough(current_bid_price, backstop_bid_price, self.config['backstop_order_ignore_price']) or self.are_different_enough(current_bid['volume_remaining'], backstop_bid_volume, self.config['order_ignore_volume']):

                        self.log(
                            'Updating backstop bid, %s is different enough than %s',
                            (current_bid_price, backstop_bid_price),
                            'green',
                        )

                        self.harness.update_order(
                            current_bid,
                            backstop_bid_price,
                            backstop_bid_volume,
                            orderbook=orderbook,
                            datums=backstop_datums,
                        )
                    else:
                        self.log(
                            'Not updating backstop bid, %s is not different enough than %s',
                            (current_bid_price, backstop_bid_price),
                        )

            except InsufficientFundsError:
                self.log('InsufficientFundsError, skipping', color='red')

        if self.config.get('sell', 'yes') != 'no':
            try:
                if not current_ask:
                    self.log(
                        'Placing new Backstop Ask: %s at %s',
                        (backstop_ask_volume, backstop_ask_price),
                    )

                    self.harness.order(
                        Consts.ASK,
                        backstop_ask_volume,
                        backstop_ask_price,
                        orderbook=orderbook,
                        datums=backstop_datums,
                    )

                else:
                    current_ask_price = current_ask['price']

                    if self.are_different_enough(current_ask_price, backstop_ask_price, self.config['backstop_order_ignore_price']) or self.are_different_enough(current_ask['volume_remaining'], backstop_ask_volume, self.config['order_ignore_volume']):

                        self.log(
                            'Updating backstop ask, %s is different enough than %s',
                            (current_ask_price, backstop_ask_price),
                            'green',
                        )

                        self.harness.update_order(
                            current_ask,
                            backstop_ask_price,
                            backstop_ask_volume,
                            orderbook=orderbook,
                            datums=backstop_datums,
                        )
                    else:
                        self.log(
                            'Not updating backstop ask, %s is not different enough than %s',
                            (current_ask_price, backstop_ask_price),
                        )
            except InsufficientFundsError:
                self.log('InsufficientFundsError, skipping', color='red')

