# -*- coding: utf-8 -*-
# This creates the declarative base for emerald havoc's models, which must be
# a different declarative base than for gryphon fury, because they share some table
# names.
# Reference: http://stackoverflow.com/questions/8264686/sqlalchemy-multiple-databases-with-same-table-names-not-working

from sqlalchemy.ext.declarative import declarative_base

EmeraldHavocBase = declarative_base()
metadata = EmeraldHavocBase.metadata

def unicode_string(self):
    return unicode(self).encode('utf-8')

EmeraldHavocBase.__str__ == unicode_string   


# How to migrate a database

#   foreman run alembic revision --autogenerate -m "moved value to Text from String"
# This generates the change script
#
#   foreman run alembic upgrade head
# This Executes the latest change script.
