import rq
import random
import signal
import os
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)


# patches RQ's work horse to not die on SIGTERM
class StrongWorker(rq.Worker):
    def main_work_horse(self, job):
        """This is the entry point of the newly spawned work horse."""
        # After fork()'ing, always assure we are generating random sequences
        # that are different from the worker.
        random.seed()

        # Always ignore Ctrl+C in the work horse, as it might abort the
        # currently running job.
        # The main worker catches the Ctrl+C and requests graceful shutdown
        # after the current work is done.  When cold shutdown is requested, it
        # kills the current job anyway.
        def nothing(signal, frame):
            return
        signal.signal(signal.SIGINT, nothing)
        signal.signal(signal.SIGTERM, nothing)

        self._is_horse = True
        self.log = logger

        success = self.perform_job(job)

        # os._exit() is the way to exit from childs after a fork(), in
        # constrast to the regular sys.exit()
        os._exit(int(not success))
