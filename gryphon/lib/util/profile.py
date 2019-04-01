"""
Taken from: https://zapier.com/engineering/profiling-python-boss/
Check out that post for examples of how to use these.

These are two simple decorators that when added to a function, output
a profile of all the function calls made from within that function.
They use two different profiling methods (cprofile vs. line_profiler)
the outputs of each can be different levels of usable for different
cases, so I included both here.
"""
from collections import defaultdict
import functools
import timeit

import monkeypatch_timeit; monkeypatch_timeit.monkeypatch_timeit()
from line_profiler import LineProfiler

def do_profile(follow=[]):
    def inner(func):
        def profiled_func(*args, **kwargs):
            try:
                profiler = LineProfiler()
                profiler.add_function(func)
                for f in follow:
                    profiler.add_function(f)
                profiler.enable_by_count()
                return func(*args, **kwargs)
            finally:
                profiler.print_stats()
        return profiled_func
    return inner


import cProfile

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats(2)
    return profiled_func

# module level storage of function profile times.
# This can then be accessed by anyone who wants to see/print tick_profile results
# maps a function name to a list of profiled times
tick_profile_data = defaultdict(list)

def tick_profile(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        def run_func():
            return func(*args, **kwargs)

        t, result = timeit.timeit(run_func, number=1)
        tick_profile_data[func.__name__].append(t)
        return result
    return inner
