# -*- coding: utf-8 -*-
from delorean import Delorean
import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.dashboards.util import assets as assets_helper
from gryphon.lib import assets
import gryphon.lib.gryphonfury.fees as gryphon_fees
import gryphon.lib.gryphonfury.revenue as revenue_lib
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money

logger = get_logger(__name__)


class AssetsHandler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self):
        start_time, end_time = self.get_start_time_and_end_time()

        # Handle end_time in the future by only loading the series up to today
        now = Delorean()

        if now.datetime < end_time:
            now.truncate('day')
            end_time = now.datetime

        assets_series = assets_helper.get_assets_series(
            self.trading_db,
            start_time,
            end_time,
        )

        liabilities_series = assets_helper.get_liabilities_series(
            self.trading_db,
            start_time,
            end_time,
        )

        net_assets_series = assets_helper.calculate_net_assets_series(
            assets_series,
            liabilities_series,
        )

        starting_balance = net_assets_series[0][1]
        starting_usd_balance = starting_balance.total_usd_value(date=start_time)

        final_balance = net_assets_series[-1][1]
        final_usd_balance = final_balance.total_usd_value(date=end_time)

        change = final_usd_balance - starting_usd_balance

        burn_transactions = assets.get_burn_transactions(
            self.trading_db,
            start_time,
            end_time,
        )

        burn = Money('0', 'USD')

        # It's important to use 'is not' here as None indicates that the burn-
        # tracking feature is not set up.
        if burn_transactions is not None:

            for burn_transaction in burn_transactions:
                burn_position = burn_transaction.position

                burn += burn_position.total_usd_value(
                    date=burn_transaction.time_completed,
                )

        revenue, trading_fees, profit = revenue_lib.fast_revenue_fees_profit_in_period(
            self.trading_db,
            start_time,
            end_time,
        )

        wire_fees = gryphon_fees.get_all_wire_fees_in_period_in_usd(
            self.trading_db,
            start_time,
            end_time,
        )

        forex_flux = assets.calculate_forex_flux(
            starting_balance,
            final_balance,
            start_time,
            end_time,
        )

        expected_change = revenue - trading_fees - wire_fees - burn + forex_flux

        discrepancy = change - expected_change

        usd_net_assets_series = assets_helper.convert_balance_series_to_usd(
            net_assets_series,
        )

        flot_usd_net_assets_series = assets_helper.process_usd_series_for_flot(
            usd_net_assets_series,
        )

        usd_assets_series = assets_helper.convert_balance_series_to_usd(assets_series)
        flot_usd_assets_series = assets_helper.process_usd_series_for_flot(
            usd_assets_series,
        )

        usd_liabilities_series = assets_helper.convert_balance_series_to_usd(
            liabilities_series,
        )

        flot_usd_liabilities_series = assets_helper.process_usd_series_for_flot(
            usd_liabilities_series,
        )

        self.render_template(
            'assets.html',
            args={
                'flot_usd_net_assets_series': flot_usd_net_assets_series,
                'flot_usd_assets_series': flot_usd_assets_series,
                'flot_usd_liabilities_series': flot_usd_liabilities_series,
                'starting_usd_balance': starting_usd_balance,
                'final_usd_balance': final_usd_balance,
                'change': change,
                'burn': burn,
                'burn_transactions': burn_transactions,
                'revenue': revenue,
                'trading_fees': trading_fees,
                'wire_fees': wire_fees,
                'expected_change': expected_change,
                'discrepancy': discrepancy,
                'forex_flux': forex_flux,
            },
        )
