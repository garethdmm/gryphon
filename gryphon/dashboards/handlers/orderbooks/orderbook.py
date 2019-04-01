from collections import defaultdict
import json
import logging

from delorean import Delorean
import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.active_exchanges import ActiveExchangesMixin
from gryphon.dashboards.handlers.orderbooks import defaults
from gryphon.lib import configuration as config_lib
from gryphon.lib.configurable_object import ConfigurableObject
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = logging.getLogger(__name__)


class OrderbooksHandler(AdminBaseHandler, ActiveExchangesMixin, ConfigurableObject):
    def __init__(self, *args, **kwargs):
        super(OrderbooksHandler, self).__init__(*args, **kwargs)

        # Configurable properties with defaults.
        self.price_currency = None
        self.volume_currency = None
        self.infinitisimal = None
        self.infinity = None
        self.zero = 0
        self.trading_pairs = []
        self.DEFAULT_WIDTH = None
        self.pair_name = None

    def configure(self, configuration):
        self.init_configurable('price_currency', configuration)
        self.init_configurable('volume_currency', configuration)
        self.init_configurable('infinitisimal', configuration)
        self.init_configurable('infinity', configuration)
        self.init_configurable('zero', configuration)
        self.init_configurable('trading_pairs', configuration)
        self.init_configurable('DEFAULT_WIDTH', configuration)
        self.init_configurable('pair_name', configuration)

        # Parse as list and turn exchange names into exchange connections.
        self.trading_pair_names = config_lib.parse_configurable_as_list(
            self.trading_pairs,
        )

        self.trading_pair_names = [t.upper() for t in self.trading_pair_names]

        self.trading_pairs = []

        for trading_pair_name in self.trading_pair_names:
            e = exchange_factory.make_exchange_from_key(trading_pair_name)
            self.trading_pairs.append(e)

    @tornado.web.authenticated
    def get(self, collection_name):
        configuration = None

        if (collection_name in self.configuration['orderbook_collections']
                and collection_name in defaults.BUILTIN_ORDERBOOK_CONFIGS.keys()):

            # Combine the two configurations intelligently.
            configuration = defaults.BUILTIN_ORDERBOOK_CONFIGS[collection_name].copy()

            config_lib.dict_update_override(
                configuration,
                self.configuration['orderbook_collections'][collection_name],
            )
        elif collection_name in self.configuration['orderbook_collections']:
            configuration = self.configuration['orderbook_collections'][collection_name]
        elif collection_name in defaults.BUILTIN_ORDERBOOK_CONFIGS.keys():
            configuration = defaults.BUILTIN_ORDERBOOK_CONFIGS[collection_name]
        else:
            self.redirect('/404')
            return

        self.configure(configuration)

        template_args = self.generate_data()

        if self.get_argument('json', False) is not False:
            self.write(json.dumps({
                'levels': template_args['levels_for_exchange'],
                'orders': template_args['open_orders_for_exchange'],
            }))
        else:
            self.render_template('orderbook.html', args=template_args)

    def generate_data(self):
        gds_active = self.is_gds_connection_active()

        if gds_active is False:
            return self.generate_null_data()

        # Get query string parameters.
        query_string_high = self.get_argument('high', None)
        query_string_low = self.get_argument('low', None)
        show_orders = self.get_argument('show_orders', False) != False
        at_time = self.get_argument('at_time', None)
        no_lookback_limit = self.get_argument('no_lookback_limit', None)

        selected_exchanges = self.get_active_exchanges(self.trading_pair_names)

        # Some simple formatting of our query string parameters.
        self.no_lookback_limit = True if no_lookback_limit else False

        if at_time:
            at_time = parse(at_time).datetime

        # Get the data.
        open_orders_for_exchange = {}

        open_orders_for_exchange = self.get_open_orders_by_exchange(at_time)

        levels_for_exchange, low_bid, high_ask = self.get_orderbook_levels(
            self.gds_db,
            self.trading_pairs,
            at_time,
            selected_exchanges,
        )

        levels_for_exchange = self.format_levels_for_graphing(levels_for_exchange)

        high, low = self.determine_graph_default_range(
            query_string_high,
            query_string_low,
            low_bid,
            high_ask,
            open_orders_for_exchange,
        )

        args = {
            'gds_active': gds_active,
            'levels_for_exchange': levels_for_exchange,
            'selected_exchanges': selected_exchanges,
            'open_orders_for_exchange': open_orders_for_exchange,
            'high': high,
            'low': low,
            'pair_name': self.pair_name,
            'show_orders': show_orders,
            'at_time': None if not at_time else at_time.isoformat(),
        }

        return args

    def determine_graph_default_range(self, query_string_high, query_string_low, high_ask, low_bid, open_orders):
        """
        If a range is specified in the query string, use that.
        """

        # Defaults
        high = high_ask + Money(self.DEFAULT_WIDTH, self.price_currency)
        low = low_bid - Money(self.DEFAULT_WIDTH, self.price_currency)

        # Make sure we get open order prices on the graph.
        if len(open_orders) > 0:
            order_prices = []

            for exchange, exchange_orders in open_orders.items():
                for o in exchange_orders:
                    order_prices.append(o[0])

            order_prices = sorted(order_prices)

            lowest_order = order_prices[0]
            highest_order = order_prices[-1]

            # Is the parameter right here?
            if lowest_order < low:
                low = Money(str(lowest_order * 0.99), self.price_currency)

            if highest_order > high:
                high = Money(str(highest_order * 1.01), self.price_currency)

        # Query string overrides.
        if query_string_high is not None:
            high = Money(query_string_high, self.price_currency)

        if query_string_low is not None:
            low = Money(query_string_low, self.price_currency)

        return high, low

    def get_orderbook_levels(self, gds_db, trading_pairs, at_time, selected_exchanges):
        orderbooks = self.get_all_orderbooks(
            self.trading_pairs,
            self.gds_db,
            at_time,
        )

        levels_for_exchange, low_bid, high_ask = self.get_levels_from_orderbooks(
            orderbooks,
            selected_exchanges=selected_exchanges,
        )

        return levels_for_exchange, low_bid, high_ask

    def generate_null_data(self):
        open_orders_for_exchange = {}
        orderbooks = defaultdict(lambda x: [])
        levels_for_exchange = {e: [] for e in self.trading_pair_names}

        args = {
            'gds_active': False,
            'levels_for_exchange': levels_for_exchange,
            'selected_exchanges': [''],
            'open_orders_for_exchange': open_orders_for_exchange,
            'high': Money('1', 'USD'),
            'low': Money('0', 'USD'),
            'pair_name': self.pair_name,
            'show_orders': False,
            'at_time': None,
        }

        return args

    def get_open_orders_by_exchange(self, at_time=None):
        """
        Get the orders in the trading database that are currently open, or optionally
        were open at some point in the past.
        """
        orders = []

        if at_time is None:
            orders = self.trading_db.query(Order)\
                .filter(Order.status == 'OPEN')\
                .filter(Order._exchange_name.in_(self.trading_pair_names))\
                .order_by(Order._price * Order.exchange_rate)\
                .all()
        else:
            orders = self.trading_db.query(Order)\
                .filter(Order._exchange_name.in_(self.trading_pair_names))\
                .filter(Order.time_created < at_time)\
                .filter(Order.time_executed > at_time)\
                .order_by(Order._price * Order.exchange_rate)\
                .all()

        open_orders = defaultdict(lambda: [])

        for order in orders:
            price = float(order.price.to('USD').amount)
            volume = float(order.volume.amount)
            order_type = order.order_type

            open_orders[order._exchange_name].append([price, volume, order_type])

        return open_orders

    def get_all_orderbooks(self, exchange_objects, gds_db, at_time=None):
        orderbooks = defaultdict(lambda x: [])

        for e in exchange_objects:
            orderbook = self.get_orderbook_for_exchange(gds_db, e, at_time)

            orderbooks[e.name] = orderbook

        return orderbooks

    def get_orderbook_for_exchange(self, gds_db, exchange, at_time=None):
        db_orderbook = None

        if at_time:
            db_orderbook = self.get_orderbook_for_exchange_at_time(
                gds_db,
                exchange,
                at_time,
            )
        else:
            db_orderbook = self.get_latest_orderbook_for_exchange(gds_db, exchange)

        if db_orderbook is None:
            return None

        raw_orderbook = {
            'bids': db_orderbook.bids,
            'asks': db_orderbook.asks,
        }

        orderbook = exchange.parse_orderbook(raw_orderbook, cached_orders=True)

        return orderbook

    def get_latest_orderbook_for_exchange(self, gds_db, exchange):
        orderbook = None

        if self.no_lookback_limit is True:
            orderbook = gds_db.query(Orderbook)\
                .filter(Orderbook.exchange == exchange.name.upper())\
                .order_by(Orderbook.timestamp.desc())\
                .first()
        else:
            # We only show orderbooks from the last hour.
            now = Delorean()
            latest_orderbook_time = now.naive
            earliest_orderbook_time = now.last_hour(1).naive

            orderbook = gds_db.query(Orderbook)\
                .filter(Orderbook.exchange == exchange.name.upper())\
                .filter(Orderbook.timestamp > earliest_orderbook_time)\
                .filter(Orderbook.timestamp <= latest_orderbook_time)\
                .order_by(Orderbook.timestamp.desc())\
                .first()

        return orderbook

    def get_orderbook_for_exchange_at_time(self, gds_db, exchange, at_time):
        """
        TODO:
          - this should also have some time bounds on it. And shouldn't it be the
            first orderbook before `at_time`?
        """
        orderbook = gds_db.query(Orderbook)\
            .filter(Orderbook.exchange == exchange.name.upper())\
            .filter(Orderbook.timestamp > at_time)\
            .order_by(Orderbook.timestamp.asc())\
            .first()

        return orderbook

    def get_levels_from_orderbooks(self, orderbooks, selected_exchanges=[]):
        levels_for_exchange = {}

        low_bid = Money(self.infinity, self.price_currency)
        high_ask = Money(self.zero, self.price_currency)

        for exchange_name, orderbook in orderbooks.items():
            if orderbook == None:
                levels_for_exchange[exchange_name] = None
                continue

            levels, top_bid, top_ask = self.get_levels_from_orderbook_in_usd(orderbook)

            if top_bid < low_bid and exchange_name.upper() in selected_exchanges:
                low_bid = top_bid

            if top_ask > high_ask and exchange_name.upper() in selected_exchanges:
                high_ask = top_ask

            levels_for_exchange[exchange_name] = levels

        return levels_for_exchange, low_bid, high_ask

    def get_levels_from_orderbook_in_usd(self, orderbook):
        levels = []
        total_bid_volume = Money('0', self.volume_currency)
        total_ask_volume = Money('0', self.volume_currency)

        for order in orderbook['bids']:
            price_in_btc = order.price

            total_bid_volume += order.volume
            levels.append([price_in_btc, total_bid_volume])

        for order in orderbook['asks']:
            price_in_btc = order.price

            total_ask_volume += order.volume
            levels.append([price_in_btc, total_ask_volume])

        # Extra operations to massage the data a little bit.

        # Set fake orders at zero volume just on the inside of the top bid and ask
        # so that we can see the inside spread on graphs.
        top_bid = orderbook['bids'][0].price
        levels.append([
            top_bid + Money(self.infinitisimal, self.price_currency),
            Money('0', self.volume_currency),
        ])

        top_ask = orderbook['asks'][0].price
        levels.append([
            top_ask - Money(self.infinitisimal, self.price_currency),
            Money('0', self.volume_currency),
        ])

        levels = sorted(levels, key=lambda l: l[0].amount)

        return levels, top_bid, top_ask

    def format_levels_for_graphing(self, exchange_levels):
        formatted_levels = {}

        for exchange_name, levels in exchange_levels.items():
            if levels == None:
                formatted_levels[exchange_name] = []
                continue

            formatted_levels[exchange_name] = self.format_levels(levels)

        return formatted_levels

    def format_levels(self, levels):
        formatted_levels = []

        for price, volume in levels:
            formatted_levels.append([
                float(price.amount),
                float(volume.amount),
            ])

        if len(formatted_levels) < 1:
            return []

        return formatted_levels

