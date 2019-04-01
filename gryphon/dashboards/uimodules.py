from delorean import Delorean
import tornado.web

from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class StartEnd(tornado.web.UIModule):
    def render(self, start_time, end_time):
        formatted_start_time = self.format_date_for_title(start_time)
        formatted_end_time = self.format_date_for_title(end_time)

        prev_url, next_url = self.get_prev_and_next_url(start_time, end_time)

        current_day_url = self.get_current_day_url()
        current_month_url = self.get_current_month_url()

        return self.render_string(
            'templates/ui_modules/start_end.html',
            formatted_start_time=formatted_start_time,
            formatted_end_time=formatted_end_time,
            prev_url=prev_url,
            next_url=next_url,
            current_day_url=current_day_url,
            current_month_url=current_month_url,
        )

    def get_prev_and_next_url(self, start_time, end_time):
        prev_start, next_end = self.get_prev_start_and_next_end(start_time, end_time)

        prev_end = start_time
        prev_url = self.make_start_end_url(prev_start, prev_end)

        next_start = end_time
        next_url = self.make_start_end_url(next_start, next_end)

        return prev_url, next_url

    def get_current_day_url(self):
        start = Delorean().truncate('day')
        start_time = start.datetime
        end_time = start.next_day(1).datetime

        return self.make_start_end_url(start_time, end_time)

    def get_current_month_url(self):
        start = Delorean().truncate('month')
        start_time = start.datetime
        end_time = start.next_month(1).datetime

        return self.make_start_end_url(start_time, end_time)

    def make_start_end_url(self, start, end):
        args = {
            'start': self.format_date_for_url(start),
            'end': self.format_date_for_url(end),
        }

        base_url = self.request.path
        url = tornado.httputil.url_concat(base_url, args)
        return url

    def format_date_for_title(self, date):
        if date.hour == 0 and date.minute == 0 and date.second == 0:
            return date.strftime('%B %d, %Y')
        else:
            return date.strftime('%B %d, %Y %H:%M:%S')

    def format_date_for_url(self, date):
        if date.hour == 0 and date.minute == 0 and date.second == 0:
            return date.strftime('%Y-%m-%d')
        else:
            return str(date)

    def get_prev_start_and_next_end(self, dt_start, dt_end):
        start = Delorean(dt_start, 'UTC')
        end = Delorean(dt_end, 'UTC')

        if start.next_year(1) == end:
            prev_start = start.last_year(1)
            next_end = end.next_year(1)
        elif start.next_month(1) == end:
            prev_start = start.last_month(1)
            next_end = end.next_month(1)
        elif start.next_day(1) == end:
            prev_start = start.last_day(1)
            next_end = end.next_day(1)
        else:
            diff = dt_end - dt_start
            prev_start = dt_start - diff
            next_end = dt_end + diff
            # Returning here since we already have datetimes in this case
            return prev_start, next_end

        return prev_start.datetime, next_end.datetime
