# -*- coding: utf-8 -*-
import os

from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine
from twisted.internet import reactor


class Auditor(object):
    def start(self):
        raise NotImplementedError

    def audit(self):
        raise NotImplementedError

    def setup_mysql(self):
        self.engine = create_engine(
            os.environ.get('DB_CRED'),
            reactor=reactor,
            strategy=TWISTED_STRATEGY,
        )

