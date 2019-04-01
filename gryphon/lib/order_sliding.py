"""
You're going to place a limit order in an orderbook at a certain price, but you want to
improve the price in your favour if the orderbook is thin behind the given price. This
function 'slides' the price backwards until it finds a wall of a given strength and places
the order price to be just in front of that wall. Useful for almost any kind of limit-order
trading.

Parameters:
  orderbook, max_slide, current order price/side, jump, ignore_volume.

A couple decisions here:
  - the current max_spread logic does not actually do what it says. Instead, it gives a
    'max distance from the midpoint per order'.
      to do real max_spread we'd have to modify both orders at once
  - does midpoint matter?
      we could just call it 'max slide'

Two known use-cases here:
  - folm
  - multilinear

TODO:
  - the current logic works only on a per-order basis. I believe on some exchanges you 
    could theoretically have a situation where there are 1b 1 satoshi orders at a single
    price level, and these will all appear to be under your ignore volume.

We might make this a 'market making' library if we can think of other things to do here.
"""

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money


def is_deeper_price(mode, price_a, price_b):
    """
    price_a is deeper than price_b iff were they both on the [mode] side of an
    orderbook, price_a would be further from the center than price_b.
    """
    if mode == Consts.BID:
        return price_a < price_b
    elif mode == Consts.ASK:
        return price_a > price_b


def widen_price(mode, price, amount):
    """Push a price away from the center of the orderbook"""
    if mode == Consts.BID:
        return max(price - amount, Money('0.001', price.currency))
    elif mode == Consts.ASK:
        return price + amount


def narrow_price(mode, price, amount):
    """Push a price away towards the center of the orderbook"""
    if mode == Consts.BID:
        return price + amount
    elif mode == Consts.ASK:
        return price - amount


def slide_order(mode, initial_price, orderbook, ignore_volume=None, jump=None, max_slide=None):
    """
    Sliding an order means to move an order opportunistically deeper into an orderbook
    (to a better price for the trader) given a few conditions.

    We highly recommend always setting max_slide, but if you do not, we have arbitrary
    default boundaries defined as follows:
        bids: 0 + jump 
        asks: (10 * initial price) - jump 
    """

    new_price = None
    orderbook_side = None
    top_opposite_order = None
    volume_currency = orderbook['bids'][0].volume.currency  # Test this better.

    if ignore_volume is None:
        ignore_volume = Money('0.00000001', volume_currency)

    if jump is None:
        jump = Money('0.01', initial_price.currency)

    if max_slide is not None:
        widest_allowed_price = widen_price(mode, initial_price, max_slide)
    else:
        widest_allowed_price = narrow_price(
            mode,
            widen_price(mode, initial_price, 10 * initial_price),
            jump,
        )
    
    if mode == Consts.BID:
        orderbook_side = orderbook['bids']
        top_opposite_order = orderbook['asks'][0]
    elif mode == Consts.ASK:
        orderbook_side = orderbook['asks']
        top_opposite_order = orderbook['bids'][0]

    for order in orderbook_side:
        if (is_deeper_price(mode, order.price, initial_price)
                and order.volume > ignore_volume):

            slid_price = narrow_price(mode, order.price, jump)

            if is_deeper_price(mode, initial_price, slid_price):
                # This catches the case where due to the value of jump, we actually
                # slid to a worse price.
                new_price = initial_price
            elif is_deeper_price(mode, top_opposite_order.price, slid_price):
                # This catches the case where we accidentally crossed the spread.
                new_price = initial_price
            elif is_deeper_price(mode, slid_price, widest_allowed_price):
                # Don't slide past our maximum.
                new_price = widest_allowed_price
            else:
                # Everything checks out.
                new_price = slid_price

            break

    if new_price == None:
        if max_slide != None:
            new_price = widen_price(mode, initial_price, max_slide)
        else:
            new_price = jump

    return new_price
