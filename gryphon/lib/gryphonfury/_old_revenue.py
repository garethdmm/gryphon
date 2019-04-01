"""
Legacy profit functions, shoul be used only for testing new functions.
"""

from operator import attrgetter

from sqlalchemy.orm import joinedload

from gryphon.lib.logger import get_logger
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
import gryphon.lib.gryphonfury.positions as positions
import gryphon.lib.gryphonfury.revenue as revenue_lib

logger = get_logger(__name__)


def revenue_fees_profit_in_period(db, start_time, end_time):
    """
    This function is an easy interface to getting revenue, fees, and profit, using
    the identical flow of functions that pentecost presently uses for the trading
    dashboard. This is unused at present but is added here for reference and for
    verifying the fast_(revenue|profit) functions below.
    """

    trades = db\
        .query(Trade)\
        .join(Order)\
        .filter(Order.actor == "Multi")\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order').joinedload('datums'))\
        .all()

    trades.sort(key=attrgetter('time_created'))

    # Get the system position up until the starting point of our graph.
    open_position_offset = positions.fast_position(
        db,
        end_time=start_time,
    )

    position_trades = revenue_lib.open_position_trades(
        open_position_offset,
        db,
        start_time,
    )

    matched_trades, _ = revenue_lib.split_trades(
        position_trades + trades,
    )

    profit, revenue, fees, _ = revenue_lib.profit_data(matched_trades)

    return revenue, fees, profit


def revenue_in_period(db, start_time, end_time):
    """
    Simple function interface to the legacy revenue code. Used for verifying the more
    efficient versions.
    """

    revenue, _, _ = revenue_fees_profit_in_period(db, start_time, end_time)
    return revenue


def profit_in_period(db, start_time, end_time):
    """
    Simple function interface to the legacy profit code. Used for verifying the more
    efficient versions.
    """

    _, _, profit = revenue_fees_profit_in_period(db, start_time, end_time)
    return profit

