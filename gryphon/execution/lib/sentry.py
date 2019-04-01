"""
A bare-bones wrapper class that allows us to turn off sentry logging if we don't want
to use it (e.g. in testing).
"""

import os

import raven


class Sentry(object):
    def __init__(self, is_active=False):
        self.is_active = is_active
        self.sentry = None

        if self.is_active is True:
            self.sentry = raven.Client(os.environ['SENTRY_URL'])

    def captureException(self):
        if self.is_active is True:
            self.sentry.captureException()
