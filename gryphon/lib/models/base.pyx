# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

def unicode_string(self):
    return unicode(self).encode('utf-8')

Base.__str__ == unicode_string   


# How to migrate a database

#   foreman run alembic revision --autogenerate -m "moved value to Text from String"
# This generates the change script
#
#   foreman run alembic upgrade head
# This Executes the latest change script.
