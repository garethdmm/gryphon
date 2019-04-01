"""
A bare-bones wrapper class that allows us to turn off heartbeating if we don't want it.
"""

import subprocess


class Heartbeat(object):
    def __init__(self, is_active=False):
        self.is_active = is_active

    def heartbeat(self, heartbeat_key):
        if self.is_active is True:
            filename = 'monit/heartbeat/%s.txt' % heartbeat_key
            subprocess.call(['touch', filename])

