"""
Integration test of models (with test database connection !)
"""

import unittest
import nose

from . import factories
from ...dashboards import models
from ...dashboard_db_if import scoped_session

#
# def setup():
#     # module setup for testing : create all DB content
#     models.Base.metadata.create_all()


class MyTest(unittest.TestCase):

    def setUp(self):
        # Prepare a new, clean session, on sqllite DB # TODO : make that parametrizable (maybe via fixtures)
        self.session = scoped_session(None)  # relying on the engine setup by another module...
        # passing current session to factories
        factories.UserFactory.set_sqlalchemy_session(self.session)

    def test_something(self):
        u = factories.UserFactory()
        #self.session.commit()
        self.assertEqual([u], self.session.query(models.User).all())

    def tearDown(self):
        # Rollback the session => no changes to the database
        self.session.rollback()
        # Remove it, so that the next test gets a new Session()
        self.session.remove()


if __name__ == '__main__':
    nose.runmodule()
