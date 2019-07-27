#!/usr/bin/env python
"""
This module holds details regarding DB connection and is runnable standalone to verify integration with DB.
"""

from __future__ import absolute_import

import sqlalchemy
import sqlalchemy.orm as orm

# Session holds the SQLAlchemy session
# first a sessionmaker, it then gets configured by setting an engine, and finally turned into a scoped_session.
Session = orm.sessionmaker()
# TODO : better API design here...


def db_creds():
    import os
    return os.environ['DASHBOARD_DB_CRED']


def create_engine(creds, **kwargs):
    extra_kwargs = {
        'echo': False,
        # commenting for sqlite compatibility
        #        'pool_size': 3,
        #        'pool_recycle': 3600,
    }
    extra_kwargs.update(kwargs)
    engine = sqlalchemy.create_engine(
        creds, ** extra_kwargs
    )

    # early engine bind, in case a client uses sqlalchemy directly
    Session.configure(bind=engine)

    return engine


def scoped_session(engine=None):
    global Session

    if engine is not None:
        # binding engine as argument present can mean override of previous create_engine calls
        Session.configure(bind=engine)

    # creating session
    Session = orm.scoped_session(Session)
    return Session


if __name__ == '__main__':

    import os
    # TODO : integrate with configuration
    # TODO : make sure we connect to existing one, not creating a new one (careful with sqlite !)
    os.environ['DASHBOARD_DB_CRED'] = 'sqlite:///test_dashboard.db'

    try:
        # basic integration test verifying the database connection is successful.
        s = scoped_session(db_creds())
        s.query("1").from_statement(sqlalchemy.text("SELECT 1")).all()
        print('Works !')
    except:
        print("Broken !")
