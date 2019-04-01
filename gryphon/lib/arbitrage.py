"""
Arbitrage library. Takes in orderbooks and gives back information about arbitrage
opportunities present in them.

The current orderbook format is a dictionary of bid and ask exchange orders. This could
be changed as part of a larger refactor to bring all our orderbook representations to a
single standard.

IMPORTANT:
  - the 'Order' used here is gryphon.lib.exchange.exchange_order, not the database
    order model.
"""

from collections import defaultdict
import itertools

from cdecimal import Decimal

from gryphon.lib.logger import get_logger
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook
from gryphon.lib.money import Money
from gryphon.lib.metrics import midpoint

logger = get_logger(__name__)


CURRENCY_MISMATCH_ERROR_MESSAGE = """\
Orderbooks do not have the same volume currency. A: %s, B: %s\
"""


class MismatchedVolumeCurrenciesError(Exception):
    def __init__(self, cur_a, cur_b):
        self.message = CURRENCY_MISMATCH_ERROR_MESSAGE % (cur_a, cur_b)


class Cross(object):
    """
    Represents a cross between the bids and asks two orderbooks, whether or not that
    cross is a profitable arbitrage opportunity.
    """
    def __init__(self, volume, revenue, fees, buy_ob=None, sell_ob=None, buy_ex=None, sell_ex=None):
        self.volume = volume
        self.revenue = revenue
        self.fees = fees
        self.buy_orderbook = buy_ob
        self.sell_orderbook = sell_ob

        self.buy_exchange = buy_ob['asks'][0].exchange if buy_ob else None
        self.sell_exchange = sell_ob['bids'][0].exchange if sell_ob else None

    @property
    def volume_currency(self):
        return self.buy_exchange.volume_currency

    @property
    def price_currency(self):
        return self.buy_exchange.currency

    @property
    def profit(self):
        return self.revenue - self.fees

    def __nonzero__(self):
        """
        A cross is falsy if there is no overlap volume.
        """
        return bool(self.volume)


def detect_cross(ob1, ob2, ignore_unprofitable=True):
    """
    Look for orderbook overlap between two exchanges that could be arbitraged in either
    direction.

    Returns a Cross or None if no overlap found.
    """
    cross = detect_directional_cross(ob1, ob2, ignore_unprofitable)

    if cross is None:
        cross = detect_directional_cross(ob2, ob1, ignore_unprofitable)

    return cross


def detect_directional_cross(buy_ob, sell_ob, ignore_unprofitable=True):
    """
    Calculates the volume by which buy_ob's asks cut into sell_ob's bids, and the
    profit that could be gleaned if one could take the arbitrage. By default will not
    return a cross if it is not profitable to take advantage of given the fee brackets
    on the two pairs. This can be turned off by setting the argument ignore_unprofitable
    to False.

    Returns a Cross object containing the total volume of the overlap, the expected
    revenue and expected fees if one were to take the full opportunity. By default

    Notes:
      - The orderbook arguments are named for the action you take, not the type of order
        you are looking at. If you want to buy on ob1 and sell on ob2, you look at the
        asks on ob1 (buy_ob) and the bids on ob2 (sell_ob).
      - This supports considering orderbooks with different price currencies, since
        that is a common operation. However, if you wish to use this for price
        currencies with high hourly or even minute-ly volatility (like BTC, ETH or any
        other cryptocurrency), the speed at which exchange rates are updated in the
        builtin exchange rate service--OpenExchangeRates--may not be fast enough. It's
        strongly recommended that users do their own research on this.
      - It's important that the market order fees for the exchanges you use have be
        accurately configured.
      - In this usage 'volume' refers to the area of the overlap, which is one-half the
        total volume that would be required in orders to take the opportunity, since
        there are two exchanges.
    """

    if not buy_ob['asks'] or not sell_ob['bids']:  # A degenerate orderbook.
        return None

    buy_ex = buy_ob['asks'][0].exchange
    sell_ex = sell_ob['bids'][0].exchange

    # Detect the volume currency and check for a mismatch.
    if buy_ex.volume_currency != sell_ex.volume_currency:
      raise MismatchedVolumeCurrenciesError(
          buy_ex.volume_currency,
          sell_ex.volume_currency,
      )

    volume_currency = buy_ex.volume_currency

    # We use the buy exchange's price currency as our ground.
    base_price_currency = buy_ex.currency

    # Initialize the variables we use in the iteration phase.
    total_volume = Money('0', volume_currency)
    total_revenue = Money('0', base_price_currency)
    total_fees = Money('0', base_price_currency)

    ask_index = -1
    bid_index = -1
    ask_remaining_volume = Money('0', volume_currency)
    bid_remaining_volume = Money('0', volume_currency)
    ask = None
    bid = None

    while ask_index < len(buy_ob['asks']) - 1 and bid_index < len(sell_ob['asks']) - 1:
        if ask_remaining_volume == Money('0', volume_currency):
            ask_index += 1
            ask = buy_ob['asks'][ask_index]
            ask_price = ask.price.to(base_price_currency)
            ask_remaining_volume = ask.volume

        if bid_remaining_volume == Money('0', volume_currency):
            bid_index += 1
            bid = sell_ob['bids'][bid_index]
            bid_price = bid.price.to(base_price_currency)
            bid_remaining_volume = bid.volume

        if bid_price > ask_price:  # Found a cross
            margin = bid_price - ask_price
            volume = None

            if bid_remaining_volume > ask_remaining_volume:
                # This bid eats the whole ask.
                volume = ask_remaining_volume
            else:
                # This bid only eats part of the ask.
                volume = bid_remaining_volume

            revenue = margin * volume.amount
            total_revenue += revenue

            total_fees += bid_price * volume.amount * bid.exchange.market_order_fee
            total_fees += ask_price * volume.amount * ask.exchange.market_order_fee

            total_volume += volume
            bid_remaining_volume -= volume
            ask_remaining_volume -= volume
        else:
            break

    if total_volume:
        cross = Cross(total_volume, total_revenue, total_fees, buy_ob, sell_ob)

        if ignore_unprofitable is False:
            return cross
        elif total_revenue > total_fees:
            return cross
        else:
            return None
    else:
        return None


def get_executable_volume(cross, buy_ex_balance, sell_ex_balance):
    """
    Given a cross between two exchanges and balance information for accounts on both
    exchanges, determine how much volume of the opportunity could be taken by the
    trader.
    """

    if not cross:
        return None

    # Sell max is just whichever is lower, the volume available or the balance we have.
    sell_max = min(cross.volume, sell_ex_balance[cross.volume_currency])

    # It's a little more complicated on the buy side.
    buy_max = max_buy_volume(buy_ex_balance[cross.price_currency], cross.buy_orderbook)

    return min(buy_max, sell_max)


def detect_crosses_between_many_orderbooks(orderbooks, ignore_unprofitable=True):
    """
    Takes in a list of orderbooks and returns a list of crosses between those
    orderbooks sorted by profitability.
    """

    crosses = []

    for pair in itertools.combinations(orderbooks, 2):
        cross = detect_cross(pair[0], pair[1], ignore_unprofitable)

        if cross is not None:
            crosses.append(cross)

    crosses = sorted(crosses, key=lambda c: c.profit, reverse=True)

    return crosses


def max_buy_volume(balance, buy_orderbook):
    """
    What is the maximum volume we can buy on the given orderbook with the given balance?
    This is more complicated than it initially appears due to slippage and fees.

    It feels like this belongs in it's own library, but there isn't a clear place for it
    I can think of, so it remains here for now, nearby it's main usage.
    """
    buy_ex = buy_orderbook['asks'][0].exchange
    fee = buy_ex.market_order_fee

    vol_currency = buy_ex.volume_currency

    balance_remaining = balance
    volume_available = Money('0', vol_currency)

    for order in buy_orderbook['asks']:
        total_order_price = order.price * order.volume.amount
        total_order_fee = total_order_price * fee

        total_order_cost = total_order_price + total_order_fee

        if total_order_cost <= balance_remaining:
            balance_remaining -= total_order_cost
            volume_available += order.volume
        else:
            # With our given balance we want to use all of it, so we have:
            # (1 + fee) * (volume * price) = balance
            # volume = (balance / (1 + fee)) / price
            last_volume = (
                (balance_remaining.amount / (Decimal('1') + fee)) / order.price.amount
            )

            last_volume = Money(last_volume, vol_currency)

            volume_available += last_volume

            break

    return volume_available

