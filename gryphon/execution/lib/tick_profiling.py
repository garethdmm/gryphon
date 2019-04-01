"""
Functions we use to record tick time performance stats.
"""

from delorean import Delorean

from gryphon.lib.models.datum import Datum, DatumRecorder
from gryphon.lib.util.profile import tick_profile, tick_profile_data


TICK_SAMPLE_SIZE = 10
TICK_BLOCK_SAMPLE_SIZE = 100


def record_tick_data(tick_start, strategy_name):
    tick_end = Delorean().epoch
    tick_length = tick_end - tick_start

    datum_name = '%s_TICK_TIME' % strategy_name
    DatumRecorder().record_mean(datum_name, tick_length, TICK_SAMPLE_SIZE)


def record_tick_block_data(algo, tick_count, strategy_name):
    for function_name, profile_times in tick_profile_data.iteritems():
        datum_name = datum_name_for_function_block(strategy_name, function_name)

        for block_time in profile_times:
            DatumRecorder().record_mean(datum_name, block_time, TICK_BLOCK_SAMPLE_SIZE)

        tick_profile_data[function_name] = []


def datum_name_for_function_block(strategy_name, function_name):
    datum_name = '%s_TICK_BLOCK_TIME_%s' % (
        strategy_name.upper(),
        function_name.upper(),
    )

    return datum_name

