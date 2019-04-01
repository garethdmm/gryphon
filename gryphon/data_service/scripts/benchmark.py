# Simple test script for benchmarking regular python logging vs twisted's logging.

import logging

from twisted.internet import reactor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

log_counter = 0


def std_log():
    global log_counter
    logger.info("STD LOG TEST")
    log_counter += 1
    reactor.callLater(0, std_log)


def tx_log():
    global log_counter
    logger.info("TX  LOG TEST")
    log_counter += 1
    reactor.callLater(0, tx_log)


def stop():
    print "Log Counter: %s" % log_counter
    reactor.stop()


reactor.callLater(0, std_log)
reactor.callLater(10, stop)

reactor.run()

# Results 2015-09-24
# std_log, 10s: 88,221 logs
# tx_log, 10s: 87,307 logs
# Conclusion: negligible difference
