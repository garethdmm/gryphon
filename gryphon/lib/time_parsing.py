"""
Somewhere between 0.3 and 1.0, Delorean changed the behaviour of their 'parse' function
so that it no longer defaults to parsing strings by iso 8601. I have no idea why, it may
have to do with downstream changes in python-dateutil. In any case, this function hacks
the delorea.parse() function back into it's old behaviour.
"""

import delorean


def parse(*args, **kwargs):
    return delorean.parse(*args, dayfirst=False, **kwargs)
