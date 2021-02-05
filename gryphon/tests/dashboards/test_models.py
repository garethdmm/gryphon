"""
Integration test of models (with test database connection !)
"""

import unittest
import nose

from . import factories
from ...dashboards import models
from ...import dashboard_db_if

#
# def setup():
#     # module setup for testing : create all DB content
#     models.Base.metadata.create_all()


class MyTest(unittest.TestCase):

    def setUp(self):
        # Prepare a new, clean session, on sqllite DB # TODO : make that parametrizable (maybe via fixtures)
        self.session = dashboard_db_if.scoped_session(None)  # relying on the engine setup somewhere else...
        # passing current session to factories
        factories.UserFactory.set_sqlalchemy_session(self.session)

    def test_something(self):
        buf = self.session.query(models.User).all()
        u = factories.UserFactory()
        auf = self.session.query(models.User).all()
        assert buf != auf  # TO make SURE something gets written in the session
        self.assertEqual([u], self.session.query(models.User).all())

    def tearDown(self):
        # Rollback the session => no changes to the database
        self.session.rollback()
        # Remove it, so that the next test gets a new scoped_session()
        self.session.remove()


if __name__ == '__main__':
    nose.runmodule()
