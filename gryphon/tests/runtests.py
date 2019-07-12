"""
A simple script that allows us to run our test-suite from an installed console entry
point.
"""

import pyximport; pyximport.install(language_level=3)

import logging
import os
from pkg_resources import resource_filename
import sys

import nose

import money

def main():
    test_dir = resource_filename('gryphon', 'tests/logic')

    if 'extra' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/extra')
    elif 'environment' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/environment')

    args = [
        '-s',
        '--rednose',
        '--where=%s' % test_dir,
    ]

    result = nose.run(argv=args)

    if result is True:
        sys.exit(0)
    else:
        sys.exit(1)
