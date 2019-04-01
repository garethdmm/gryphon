# -*- coding: utf-8 -*-
import pyximport; pyximport.install()
import logging
import logging.handlers
import os
import sys

from raven import Client
from twisted.internet import reactor
from twisted.python import log
from twisted.web import client

from gryphon.data_service.auditor_task import AuditorTask
from gryphon.data_service.orderbook_poll_task import OrderbookPollTask
from gryphon.data_service.trades_poll_task import TradesPollTask
from gryphon.data_service.utilities_poll_task import UtilitiesPollTask
from gryphon.data_service.volume_poll_task import VolumePollTask


# Set up Logging.
logger = logging.getLogger('emerald-havoc-producer')

if 'SYSLOG_ADDRESS' in os.environ:
    syslog = logging.handlers.SysLogHandler(
        address=(
            os.environ['SYSLOG_ADDRESS'],
            int(os.environ['SYSLOG_PORT'])
        )
    )

    syslog.setLevel(logging.DEBUG)
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    syslog.setFormatter(logging.Formatter(format_str))
    logger.addHandler(syslog)


# Set up Exception Handling.
if 'SENTRY_DSN' in os.environ:
    twisted_sentry_client = Client(dsn='twisted+%s' % os.environ['SENTRY_DSN'])

    def logToSentry(event):
        if event.get('isError'):
            if 'failure' in event:
                f = event['failure']

                twisted_sentry_client.captureException(
                    (f.type, f.value, f.getTracebackObject()),
                )
            else:
                twisted_sentry_client.captureMessage(event['message'])

    log.addObserver(logToSentry)


def main(*args):
    exchanges = sys.argv[1:]
    OrderbookPollTask(exchanges=exchanges).start_task()

    # Hack for now so we don't start unimplemented trade pollers on the eth_btc pairs.
    non_orderbook_exchanges = [
        e for e in exchanges if all([
            x not in e for x in ['ETH', 'BCH', 'EUR']
        ])
    ]

    logger.info(non_orderbook_exchanges)

    TradesPollTask(exchanges=non_orderbook_exchanges).start_task()
    AuditorTask(exchanges=non_orderbook_exchanges).start_task()
    UtilitiesPollTask().start_task()
    VolumePollTask(exchanges=non_orderbook_exchanges).start_task()

    observer = log.PythonLoggingObserver('emerald-havoc-producer')
    observer.start()
    client._HTTP11ClientFactory.noisy = False

    reactor.run()

if __name__ == "__main__":
    main()
