# -*- coding: utf-8 -*-
from collections import defaultdict
import datetime
import logging

from cdecimal import Decimal
from delorean import Delorean
import tornado.web

from gryphon.lib.configurable_object import ConfigurableObject
from gryphon.lib.gryphonfury import positions
from gryphon.lib.gryphonfury import revenue as revenue_lib
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money
from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.dashboards.handlers.strategies.builtin_configs import BUILTIN_STRAT_CONFIGS
from gryphon.dashboards.util import queries

logger = logging.getLogger(__name__)


class StrategyTradingHandler(AdminBaseHandler, StartAndEndTimeMixin, ConfigurableObject):
    def __init__(self, *args, **kwargs):
        super(StrategyTradingHandler, self).__init__(*args, **kwargs)

        # Configurable properties with defaults.
        self.display_name = None
        self.strategy_actor = None
        self.price_currency = None
        self.volume_currency = None
        self.base_point_radius = None
        self.graph_volume_threshold = None
        self.position_graph_max = 4
        self.position_graph_min = -4

    def configure(self, configuration):
        self.init_configurable('display_name', configuration)
        self.init_configurable('strategy_actor', configuration)
        self.init_configurable('price_currency', configuration)
        self.init_configurable('volume_currency', configuration)
        self.init_configurable('base_point_radius', configuration)
        self.init_configurable('graph_volume_threshold', configuration)
        self.init_configurable('position_graph_max', configuration)
        self.init_configurable('position_graph_min', configuration)

    @tornado.web.authenticated
    def get(self, strategy_name):
        strategy_configuration = None

        if strategy_name in self.configuration['strategies']:
            strategy_configuration = self.configuration['strategies'][strategy_name]
        elif strategy_name in BUILTIN_STRAT_CONFIGS.keys():
            strategy_configuration = BUILTIN_STRAT_CONFIGS[strategy_name]
        else:
            self.redirect('/404')
            return

        self.configure(strategy_configuration)

        template_args = self.generate_data()

        self.render_template('strategy.html', args=template_args)

    def generate_data(self):
        start_time, end_time = self.get_start_time_and_end_time()
        start_end_delta = end_time - start_time

        trades, fundamental_value, open_position_trades, open_position_offset = self.get_trades_and_fundamental_value(self.strategy_actor, start_time, end_time)

        trade_data, total_volume, daily_volumes, total_position, position_series = self.basic_trade_analysis(self.strategy_actor, trades, start_end_delta, open_position_offset, start_time)

        matched_trades, position_trades = revenue_lib.split_trades(
            open_position_trades + trades,
            volume_currency=self.volume_currency,
        )

        profit, revenue, matched_fees, matched_volume_currency_fees, open_pl, open_position = self.get_current_trading_result(
            matched_trades,
            position_trades,
            self.price_currency,
            fundamental_value,
        )

        revenue_series = self.get_revenue_series(
            matched_trades,
            start_time,
        )

        template_args = {
            'price_currency': self.price_currency,
            'volume_currency': self.volume_currency,
            'trade_data': trade_data,
            'revenue_series': revenue_series,
            'position_series': position_series,
            'display_name': self.display_name,
            'profit': profit,
            'open_position': open_position,
            'open_pl': open_pl,
            'volume': total_volume,
            'matched_fees': matched_fees,
            'matched_volume_currency_fees': matched_volume_currency_fees,
            'revenue': revenue,
            'start_end_delta': start_end_delta,
            'start_timestamp': Delorean(start_time, "UTC").epoch * 1000,
            'end_timestamp': Delorean(end_time, "UTC").epoch * 1000,
            'now_timestamp': Delorean().epoch * 1000,
            'base_point_radius': float(self.base_point_radius),
            'position_graph_min': float(self.position_graph_min),
            'position_graph_max': float(self.position_graph_max),
        }

        return template_args

    def basic_trade_analysis(self, exchange_name, trades, start_end_delta, open_position_offset, start_time):
        trade_data = {}

        for key in ['core']:
            trade_data[key] = {}

            for side in ['bids', 'asks']:
                trade_data[key][side] = {}
                trade_data[key][side]['prices'] = []
                trade_data[key][side]['volumes'] = []

        total_volume = 0
        daily_volumes = defaultdict(lambda: 0)

        # start from yesterday's open position
        total_position = open_position_offset
        position_series = []

        position_series.append([
            Delorean(start_time, "UTC").epoch * 1000,
            str(open_position_offset.amount),
        ])

        for trade in trades:
            # ignore outliers from rounding errors
            if trade.volume < Money("0.0001", self.volume_currency):
                continue

            timestamp = Delorean(trade.time_created, "UTC").epoch * 1000

            if start_end_delta <= datetime.timedelta(weeks=1):
                # convert timestamp to an hour
                hour = Delorean(trade.time_created, "UTC").truncate('hour').epoch
                daily_volumes[hour] += trade.volume
            else:
                # convert timestamp to a day
                day = Delorean(trade.time_created, "UTC").truncate('day').epoch
                daily_volumes[day] += trade.volume

            total_volume += trade.volume

            price = trade.price_in_currency(self.price_currency)

            unit_price = price / trade.volume.amount

            trade_type = 'core'
            datums = {}

            for datum in trade.order.datums:
                datums[datum.datum_type] = datum

            if trade.volume > self.graph_volume_threshold:
                if trade.trade_type == Trade.BID:
                    side = "bids"
                else:
                    side = "asks"

                trade_data[trade_type][side]['prices'].append([
                    timestamp,
                    str(unit_price.amount),
                    trade.order.exchange.friendly_name,
                    str(trade.volume),
                    str(unit_price),
                    str(trade.fee),
                    trade.order.order_id,
                ])

                trade_data[trade_type][side]['volumes'].append(
                    str(trade.volume.amount)
                )

            total_position += trade.position[self.volume_currency]

            position_series.append([timestamp, str(total_position.amount)])

        return trade_data, total_volume, daily_volumes, total_position, position_series

    def get_revenue_series(self, matched_trades, start_time):
        total_revenue = 0
        revenue_series = []

        profit_units = revenue_lib.profit_units(matched_trades)

        for unit in profit_units:
            timestamp = Delorean(unit['time'], "UTC").epoch * 1000
            total_revenue += unit['revenue']

            revenue_series.append([timestamp, str(total_revenue.amount)])

        return revenue_series

    def get_current_trading_result(self, matched_trades, position_trades, currency, fundamental_value=None):
        profit, revenue, fees, volume_currency_fees = revenue_lib.profit_data(
            matched_trades,
            currency,
            volume_currency=self.volume_currency,
        )

        if fundamental_value:
            open_pl = revenue_lib.open_pl(
                position_trades,
                fundamental_value,
                currency,
                volume_currency=self.volume_currency,
            )
        else:
            open_pl = None

        open_position = positions.position_delta(
            position_trades,
            volume_currency=self.volume_currency,
        )[self.volume_currency]

        return profit, revenue, fees, volume_currency_fees, open_pl, open_position

    def get_trades_and_fundamental_value(self, exchange, start_time, end_time):
        start_time = queries.strip_datetime_for_db_operations(start_time)
        end_time = queries.strip_datetime_for_db_operations(end_time)

        trades = queries.get_strategy_trades_for_period(
            self.trading_db,
            self.strategy_actor,
            start_time,
            end_time,
        )

        latest_order = queries.get_strategy_latest_order(
            self.trading_db,
            self.strategy_actor,
            start_time,
            end_time,
        )

        open_position_offset = Money('0', self.volume_currency)
        open_position_trades = []

        open_position_offset = positions.fast_position(
            self.trading_db,
            end_time=start_time,
            volume_currency=self.volume_currency,
            actor=self.strategy_actor,
        )

        open_position_trades = revenue_lib.open_position_trades(
            open_position_offset,
            self.trading_db,
            start_time,
            volume_currency=self.volume_currency,
            strategy_actor=self.strategy_actor,
        )

        fundamental_value = None

        if latest_order and latest_order.fundamental_value:
            fundamental_value = latest_order.fundamental_value

            if self.price_currency == "USD":
                fundamental_value = fundamental_value.to(
                    "USD",
                    exchange_rate_to_usd=latest_order.exchange_rate,
                )

        return trades, fundamental_value, open_position_trades, open_position_offset

