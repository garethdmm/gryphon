import logging

import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.lib.gryphonfury import fees

logger = logging.getLogger(__name__)


class FeesDashboardHandler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self):
        start_time, end_time = self.get_start_time_and_end_time()

        total_trading_fees = fees.get_all_fees_in_period_in_usd(
            self.trading_db,
            start_time,
            end_time,
        )

        fees_by_exchange = fees.get_all_fees_in_period_by_exchange_in_usd(
            self.trading_db,
            start_time,
            end_time,
        )

        total_wire_fees = fees.get_all_wire_fees_in_period_in_usd(
            self.trading_db,
            start_time,
            end_time,
        )

        wire_fees_by_exchange = fees.get_wire_fees_in_period_by_exchange(
            self.trading_db,
            start_time,
            end_time,
        )

        self.render_template(
            'fees.html',
            args={
                'total_trading_fees': total_trading_fees,
                'fees_by_exchange': fees_by_exchange,
                'total_wire_fees': total_wire_fees,
                'wire_fees_by_exchange': wire_fees_by_exchange,
            },
        )

