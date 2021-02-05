from __future__ import absolute_import

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


# We want that at the highest level to make it easy to be changed depending on usecases
#  see 'clean architecture' / hexagonal architecture / domain driven design principles
from .. import dashboard_db_if


def runtests(test_directory, execute=False):
    """ Actually runs the tests in that directory
        :param execute: Tests are run with side-effects !!!
    """
    import sqlalchemy

    # Architecture Ref : https://factoryboy.readthedocs.io/en/latest/orms.html#managing-sessions

    if execute:
        # TODO : load configuration
        # Use the database from configuration (BEWARE: tests should strive to not leave any change behind !)
        creds = dashboard_db_if.db_creds()  # TODO : maybe add suffix to DB ??
        # TODO : run migrations here (first setup)
        print("Using DB : " + creds)
        # TMP: WIP
        print("Aborting before anything happens. '--execute' tests mode is still under development, and could easily break things...")
        sys.exit(127)
    else:
        default_creds = "sqlite://"  # default : in memory DB
        default_engine_kwargs = {
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
            'echo': True,
        }
        dashboard_db_if.setup_engine(default_creds, **default_engine_kwargs)

    args = [
        '-s',
        '--rednose',
        '--verbosity=2',
        '--where=%s' % test_directory,
    ]

    return nose.run(argv=args)


def main():
    # TODO : better way to get CLI arguments for '--execute'
    if len(sys.argv)>1 and sys.argv[1] == '--execute':
        execute = True
    else:
        execute = False

    test_dir = resource_filename('gryphon', 'tests/logic')

    if 'extra' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/extra')
    elif 'environment' in sys.argv:
        test_dir = resource_filename('gryphon', 'tests/environment')

    result = runtests(test_dir, execute=execute)

    # Integrating new dashboard tests
    dashboard_test_dir = resource_filename('gryphon', 'tests/dashboards')

    dashboard_result = runtests(dashboard_test_dir, execute=execute)

    if result and dashboard_result:
        sys.exit(0)
    else:
        sys.exit(1)
