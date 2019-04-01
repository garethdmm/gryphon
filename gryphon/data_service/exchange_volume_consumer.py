import pyximport; pyximport.install()

import json
import os
import subprocess

from delorean import epoch
from raven import Client

from gryphon.data_service.consts import *
from gryphon.data_service.queue_consumer import QueueConsumer
from gryphon.lib import session
from gryphon.lib.models.emeraldhavoc.exchange_volume import ExchangeVolume
from gryphon.lib.money import Money


s = Client(dsn=os.environ.get('SENTRY_DSN'))


def exchange_volumes_consumer_function(message, db):
    subprocess.call(['touch', 'monit/heartbeat/exchange_volumes_consumer.txt'])

    exchange_volume_json = json.loads(message)
    timestamp = epoch(exchange_volume_json['timestamp']).datetime
    exchange = exchange_volume_json['exchange_name']
    exch_vol_money = Money(exchange_volume_json['volume'], 'BTC')

    t = ExchangeVolume(
        exchange_volume=exch_vol_money,
        exchange=exchange,
        timestamp=timestamp,
    )

    db.add(t)

    session.commit_mysql_session(db)


def main():
    db = session.get_a_gds_db_mysql_session()

    try:
        volume_consumer = QueueConsumer(
            os.environ.get('AMPQ_ADDRESS'),
            exchange_volumes_consumer_function,
            db,
            EXCHANGE,
            EXCHANGE_TYPE,
            EXCHANGE_VOLUME_BINDING_KEY,
            EXCHANGE_VOLUME_QUEUE,
        )

        volume_consumer.run()
    except KeyboardInterrupt:
        volume_consumer.stop()
    except:
        s.captureException()
    finally:
        db.remove()


if __name__ == '__main__':
    main()
