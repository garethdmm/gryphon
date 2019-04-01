import termcolor as tc
import time

from gryphon.execution.strategies.base import Strategy
from gryphon.execution.strategies.harness import Harness
from gryphon.execution.lib.exchange_color import exchange_color
from gryphon.lib import session
from gryphon.lib.exchange.exchange_factory import *
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


def wind_down(exchange_name, strategy_params, execute=False):
    db = session.get_a_trading_db_mysql_session()

    try:
        strategy = Strategy(
            make_exchange_from_key(exchange_name),
            db,
            debug=False,
            backtest=False,
            execute=execute,
            params=strategy_params,
        )

        harness = Harness(strategy, db)
        harness.wind_down()
    finally:
        session.commit_mysql_session(db)
        db.remove()
