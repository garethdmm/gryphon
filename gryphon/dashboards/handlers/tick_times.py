from admin_base import AdminBaseHandler
import tornado.web

from mixins.start_and_end_time import StartAndEndTimeMixin
from tinkerpy.exchange.exchange_factory import all_exchanges
import util.tick_times as tick_times


class TickTimesHandler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self):
        start_time, end_time = self.get_start_time_and_end_time()

        all_tick_time_series = self.get_all_ticktime_series(start_time, end_time)

        self.render_template(
            'tick_times.html',
            args={
                'all_tick_time_series': all_tick_time_series,
            },
        )

    def get_all_ticktime_series(self, start_time, end_time):
        exchange_list = all_exchanges()

        all_tick_time_series = {}

        for exchange in exchange_list:
            tick_time_series = tick_times.get_ticktime_series_for_exchange(
                self.trading_db,
                exchange.name,
                start_time,
                end_time,
            )

            all_tick_time_series[exchange.name] = tick_time_series

        return all_tick_time_series
