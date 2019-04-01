from admin_base import AdminBaseHandler
import tornado.web

from mixins.start_and_end_time import StartAndEndTimeMixin
import util.tick_times as tick_times


class BlockTimesHandler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self, exchange_name=None):
        start_time, end_time = self.get_start_time_and_end_time()

        page_title = '%s Tick Block Times' % (
            exchange_name.capitalize(),
        )

        all_block_time_series = tick_times.get_tick_block_time_series_for_exchange(
            self.trading_db,
            exchange_name,
            start_time,
            end_time,
        )

        self.render_template(
            'block_times.html',
            args={
                'page_title': page_title,
                'all_block_time_series': all_block_time_series,
            },
        )
