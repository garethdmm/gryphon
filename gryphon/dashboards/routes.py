# -*- coding: utf-8 -*-
import os

import tornado.web

from gryphon.dashboards.handlers.assets import AssetsHandler
from gryphon.dashboards.handlers.balances import AllBalancesHandler
#from gryphon.dashboards.handlers.block_times import BlockTimesHandler
from gryphon.dashboards.handlers.fees import FeesDashboardHandler
from gryphon.dashboards.handlers.home import HomeHandler
from gryphon.dashboards.handlers.ledger import LedgerHandler
from gryphon.dashboards.handlers.login import LoginHandler
from gryphon.dashboards.handlers.logout import LogoutHandler
from gryphon.dashboards.handlers.notfound import NotFoundHandler
from gryphon.dashboards.handlers.orderbooks.orderbook import OrderbooksHandler
from gryphon.dashboards.handlers.status import GryphonStatusHandler
#from gryphon.dashboards.handlers.tick_times import TickTimesHandler
from gryphon.dashboards.handlers.trade_view import TradeViewHandler
from gryphon.dashboards.handlers.strategies.strategy import StrategyTradingHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ROOT = os.environ['APP_ROOT']
SRC_ROOT = os.path.join(ROOT, APP_ROOT)


url_patterns = [
    (r"/?", HomeHandler),
    (r"/404", NotFoundHandler),
    (r"/balances/?", AllBalancesHandler),
    (r"/assets/?", AssetsHandler),
    (r"/status/?", GryphonStatusHandler),
    (r"/fees/?", FeesDashboardHandler),
#    (r"/ticktimes/?", TickTimesHandler),
#    (r"/block_times/(.+)/?", BlockTimesHandler),
    (r"/orderbooks/(.+?)/?", OrderbooksHandler),
    (r"/ledger/(.+?)(?:/(.+?))?/?", LedgerHandler),
    (r"/strategies/(.+?)/?", StrategyTradingHandler),
    (r"/tradeview/?", TradeViewHandler),
    (r"/login/?", LoginHandler),
    (r"/logout/?", LogoutHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': '%s/static' % SRC_ROOT}),
]
