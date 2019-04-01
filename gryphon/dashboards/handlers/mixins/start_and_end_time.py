"""
This adds a single function on the handler that gets query string arguments 'start' and
'end' and returns them as dates. The format for the arguments should be %Y-%m-%d,
e.g. 2015-10-22.

Optional parameters default_start and default_end specify what values the function
should return if either argument does not exist in the query string.
"""

from delorean import Delorean

from gryphon.lib.time_parsing import parse


class StartAndEndTimeMixin():
    def get_start_time_and_end_time(self, default_start=None, default_end=None):
        start = self.get_argument('start', None)
        end = self.get_argument('end', None)

        start_time = None
        end_time = None

        if start:
            start_time = parse(start).datetime
        elif default_start:
            start_time = default_start
        else:
            start_time = Delorean().truncate('day').datetime

        if end:
            end_time = parse(end).datetime
        elif default_end:
            end_time = default_end
        else:
            end_time = Delorean(start_time, 'UTC').next_day(1).datetime

        return start_time, end_time
