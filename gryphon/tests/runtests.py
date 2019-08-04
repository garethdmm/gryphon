"""
A simple script that allows us to run our test-suite from an installed console entry
point.
"""

import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

import logging
import os
from pkg_resources import resource_filename
import sys

import pytest


def main():
    test_dir = resource_filename('gryphon', 'tests/logic')

    if 'extra' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/extra')
    elif 'environment' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/environment')

    args = [
        '-s',
        test_dir
    ]

    result = pytest.main(args=args)

    sys.exit(result)


if __name__ == "__main__":
    main()
