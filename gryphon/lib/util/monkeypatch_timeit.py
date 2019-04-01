"""
Monkeypatch the timeit module so that it returns a function result as well
as the time it took to execute the function. This is used to profile ticks
in production.
"""
import timeit

def _template_func(setup, func):
    """Create a timer function. Used if the "statement" is a callable."""
    def inner(_it, _timer, _func=func):
        setup()
        _t0 = _timer()
        for _i in _it:
            retval = _func()
        _t1 = _timer()
        return _t1 - _t0, retval
    return inner

def monkeypatch_timeit():
    timeit._template_func = _template_func
