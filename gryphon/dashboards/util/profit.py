from operator import attrgetter

import gryphon.lib.gryphonfury.positions as positions
import gryphon.lib.gryphonfury.revenue as revenue_lib
import gryphon.dashboards.util.queries as queries


def get_trades_and_position_trades(db, start_time, end_time):
    """
    There is still a missing refactor in all our profit calculation code
    there's a bit of duplication in gryphon handler and I think the whole
    thing could still be simpler.
    """
    trades = queries.get_all_trades_for_period(
        db,
        start_time,
        end_time,
    )

    trades.sort(key=attrgetter('time_created'))

    # get system position up until the starting point of our graph
    open_position_offset = positions.fast_btc_position(
        db,
        end_time = start_time,
    )

    open_position_trades = revenue_lib.open_position_trades(
        open_position_offset, 
        db,
        start_time,
    )

    return trades, open_position_trades

