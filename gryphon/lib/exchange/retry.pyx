"""
A decorator that retries exchange requests if they fail.
"""

import functools
from retrying import Retrying

import gryphon.lib.exchange.exceptions as exceptions


def retry_if_exchange_exception(exception):
    return isinstance(exception, exceptions.ExchangeAPIFailureException) or isinstance(exception, exceptions.NonceError)


def exchange_retry():
    """
    Decorator that retries exchange requests with an exponential backoff between 1 and 128
    seconds.
    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return Retrying(
                retry_on_exception=retry_if_exchange_exception,
                wait_exponential_multiplier=1000,
                stop_max_attempt_number=7,
            ).call(function, *args, **kwargs)
        return wrapper
    return decorator

