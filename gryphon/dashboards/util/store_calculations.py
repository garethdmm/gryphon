import cdecimal
import functools
import simplejson as json
from cdecimal import Decimal
from delorean import Delorean
from gryphon.lib import gryphon_json_serialize
from gryphon.lib.logger import get_logger
from gryphon.lib.session import get_a_redis_connection

logger = get_logger(__name__)

"""
    A decorator which stores the result of the function in a redis database

    This is specifically to be used for storing the result of cpu intensive
    calculations which will not change any time in the future.

    This only works with functions on a handler object. We can exted it
    later to work with library and util functions.

    Be *very* careful not to use this on any functions whose results will
    change over time, e.g. calculation revenues for the present month.

    An example usage is investor.py:get_total_vllume_for_exchange_in_period

    You can force the handlers to recalculate any calculations by passing
    &recalculate in the query string.
"""
def store_calculation_result(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        handler = args[0]

        # remove the 'self' argument on the handlers
        key_args = args[1:]

        # keys in redis are a stringifying of the function name and
        # arguments.
        key = '%s:%s:%s' % (
            function.__name__, 
            str(key_args), 
            str(kwargs),
        )
  
        redis = redis = get_a_redis_connection()

        if not handler.should_recalculate_stored_results:
            redis_result = redis.get(key)

            if redis_result:    
                return parse_value_from_redis(redis_result)

        calculated_value = function(*args, **kwargs)
  
        redis.set(key, prepare_value_for_redis(calculated_value))

        return calculated_value
    return wrapper


def prepare_value_for_redis(value):
    return json.dumps(value, use_decimal=True)


def parse_value_from_redis(value):
    return json.loads(value, parse_float=Decimal)


