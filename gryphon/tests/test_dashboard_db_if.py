from __future__ import absolute_import

"""
Module to test dashboard_db_if itself
"""

import nose
import sqlalchemy

from .. import dashboard_db_if


def test_initial_sessionmaker():
    assert isinstance(dashboard_db_if.Session, sqlalchemy.orm.sessionmaker)
    # TODO : assert no engine bound


def test_db_creds():
    import os
    bkp = os.environ.get('DASHBOARD_DB_CRED')
    try:
        os.environ['DASHBOARD_DB_CRED'] = "SOMEVALUE"
        assert dashboard_db_if.db_creds() == os.environ['DASHBOARD_DB_CRED']
    finally:
        if bkp:
            os.environ['DASHBOARD_DB_CRED'] = bkp


def test_session():

    # testing with in memoryDB for no side effects
    s = dashboard_db_if.scoped_session('sqlite://')

    assert isinstance(s, sqlalchemy.orm.scoping.scoped_session)
    assert isinstance(s.bind, sqlalchemy.engine.base.Engine)
    s.close()


if __name__ == '__main__':
    nose.runmodule()

