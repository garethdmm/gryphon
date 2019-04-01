# -*- coding: utf-8 -*-
# This creates the declarative base for the analytics database models, which must be
# a different declarative base than for any of our other database, because they may
# share some table names.
# Reference: http://stackoverflow.com/questions/8264686/sqlalchemy-multiple-databases-with-same-table-names-not-working

from sqlalchemy.ext.declarative import declarative_base

AtlasZeroBase = declarative_base()
metadata = AtlasZeroBase.metadata


def unicode_string(self):
    return unicode(self).encode('utf-8')

AtlasZeroBase.__str__ == unicode_string


# How to migrate a database

#   foreman run alembic revision --autogenerate -m "moved value to Text from String"
# This generates the change script

#   foreman run alembic upgrade head
# This Executes the latest change script.
