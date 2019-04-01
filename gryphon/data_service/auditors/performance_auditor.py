from delorean import Delorean
from twisted.internet.task import LoopingCall
from twisted.python import log

from gryphon.data_service.auditors.auditor import Auditor


class PerformanceAuditor(Auditor):

    def start(self):
        self.time_between_calls = 10
        self.previous_timestamp = None
        self.looping_call = LoopingCall(self.audit)
        self.looping_call.start(self.time_between_calls)

    def audit(self):
        now = Delorean().epoch
        if not self.previous_timestamp:
            self.previous_timestamp = now
        else:
            expected_timestamp = self.previous_timestamp + self.time_between_calls
            actual_timestamp = now
            lag = actual_timestamp - expected_timestamp
            log.msg('Performance Lag: %.3fs' % lag)
            self.previous_timestamp = now
