"""
A simple script that allows us to run our test-suite from an installed console entry
point.
"""

import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

import logging
import os
from pkg_resources import resource_filename
import sys

import nose

import money


# TODO : we probably want that a the highest level to make it easy to change (see 'clean architecture' principles)
from .. import dashboard_db_if


def runtests():
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker

    # Get an in memory database for testing
    # TODO : somehow link that with the actual way we create a session in gryphon (functions in session.py might need some rearchitecturing...)
    # s = session.get_a_mysql_session('sqlite://')
    # Ref : https://factoryboy.readthedocs.io/en/latest/orms.html#managing-sessions

    engine = sqlalchemy.create_engine('sqlite://')

    # It's a scoped_session, and now is the time to configure it.
    dashboard_db_if.Session.configure(bind=engine)


def main():
    test_dir = resource_filename('gryphon', 'tests/logic')

    if 'extra' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/extra')
    elif 'environment' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/environment')

    args = [
        '-s',
        '--rednose',
        '--verbosity=2',
        '--where=%s' % test_dir,
    ]

    result = nose.run(argv=args)

    # Integrating new dashboard tests
    dashboard_test_dir = resource_filename('gryphon', 'tests/dashboards')

    args = [
        '-s',
        '--rednose',
        '--verbosity=2',
        '--where=%s' % dashboard_test_dir,
    ]

    dashboard_result = nose.run(argv=args)

    if result and dashboard_result:
        sys.exit(0)
    else:
        sys.exit(1)
