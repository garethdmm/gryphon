import functools
from delorean import Delorean
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

from gryphon.lib.session import get_a_memcache_connection

def _localcache_get(localcache, key):
    result = localcache.get(key)
    if not result:
        return None
    value, expiry_time = result
    if Delorean().epoch > expiry_time:
        logger.debug('Localcache for %s expired' % key)
        return None
    return value

def _localcache_set(localcache, key, value, time):
    expiry_time = Delorean().epoch + time
    logger.debug("Setting localcache %s" % expiry_time)
    localcache[key] = [value, expiry_time]

def cache_me(time=1200, ignore_self=False):
    """
    Decorator that caches the result of a method for the specified time in seconds.

    Use it as:

    @cache_me(time=1200) # 20min
    def functionToCache(arguments):
        ...

    """
    def decorator(function):
        localcache = function.localcache = {}
        memcache = get_a_memcache_connection()
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if ignore_self:
                key_args = args[1:]
            else:
                key_args = args
            key = '%s%s%s' % (function.__name__, str(key_args), str(kwargs))
            key = key.replace(" ", "_") # Memcache doesn't allow spaces in keys

            # try localcache first
            local_value = _localcache_get(localcache, key)
            logger.debug('Localcache lookup for %s, found? %s', key, local_value != None)
            if local_value:
                return local_value

            # then try memcache
            memcache_value = memcache.get(key)
            logger.debug('Memcache lookup for %s, found? %s', key, memcache_value != None)
            if memcache_value:
                _localcache_set(localcache, key, memcache_value, time)
                return memcache_value

            # otherwise calculate it
            calculated_value = function(*args, **kwargs)
            memcache.set(key, calculated_value, time=time)
            _localcache_set(localcache, key, calculated_value, time)
            return calculated_value
        return wrapper
    return decorator
