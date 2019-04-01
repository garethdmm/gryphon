import pyximport; pyximport.install()

import json
import os
import subprocess

from delorean import epoch
from raven import Client
from sqlalchemy import exc

from gryphon.data_service.consts import *
from gryphon.data_service.queue_consumer import QueueConsumer
from gryphon.lib import session
from gryphon.lib.models.emeraldhavoc.trade import Trade
from gryphon.lib.money import Money

s = Client(dsn=os.environ.get('SENTRY_DSN'))


def trades_consumer_function(message, db):
    subprocess.call(['touch', 'monit/heartbeat/trades_consumer.txt'])
    trade_json = json.loads(message)
    timestamp = epoch(trade_json['timestamp']).datetime
    price_currency = trade_json.get('price_currency', 'USD')
    volume_currency = trade_json.get('volume_currency', 'BTC')

    t = Trade(
        price=Money(trade_json['price'], price_currency),
        volume=Money(trade_json['volume'], volume_currency),
        exchange=unicode(trade_json['exchange']),
        timestamp=timestamp,
        exchange_trade_id=unicode(trade_json['trade_id']),
    )

    db.add(t)

    try:
        session.commit_mysql_session(db)
    except exc.IntegrityError as e:
        # We will get a duplicate entry error from the database if we happen to stop
        # the bot after we write the entry but before we acknowlege it to the queue.
        # This will cause an infinite loop of errors where we keep failing to write the
        # same entry. In this case we can successfully ack the message because we
        # already have it stored.
        if 'Duplicate entry' in str(e):
            return
        else:
            raise e


def main():
    db = session.get_a_gds_db_mysql_session()

    try:
        trades_consumer = QueueConsumer(
            os.environ.get('AMPQ_ADDRESS'),
            trades_consumer_function,
            db,
            EXCHANGE,
            EXCHANGE_TYPE,
            TRADES_BINDING_KEY,
            TRADES_QUEUE,
        )

        trades_consumer.run()
    except KeyboardInterrupt:
        trades_consumer.stop()
    except:
        s.captureException()
    finally:
        db.remove()


if __name__ == '__main__':
    main()
