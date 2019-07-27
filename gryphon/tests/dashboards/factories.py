from __future__ import absolute_import

import factory
import sqlalchemy
from ...dashboards import models
from ...import dashboard_db_if

dashboard_db_if.Session.configure(autoflush=False)

engine = dashboard_db_if.create_engine(
    'sqlite://',
    connect_args={'check_same_thread':False},
    poolclass=sqlalchemy.pool.StaticPool,
    echo=True,
)

# creating all tables upon factories.py import
models.Base.metadata.create_all(bind=engine)


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        # sqlalchemy_session should be set when session setup by test case.

    #TODO : fix this hack
    @classmethod
    def set_sqlalchemy_session(cls, session):
        """Dynamically set the session
           Should be called before creating an instance of this class.
        """
        cls._meta.sqlalchemy_session = session

    username = factory.Sequence(lambda n: "User %d" % n)
    password = factory.Sequence(lambda n: n)

# TODO : better password checks
