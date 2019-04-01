import pyximport; pyximport.install()
import json
import os
import subprocess

from delorean import epoch
from raven import Client

import gryphon.data_service.consts as consts
from gryphon.data_service.queue_consumer import QueueConsumer
from gryphon.lib import session
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook


s = Client(dsn=os.environ.get('SENTRY_DSN'))


def orderbook_consumer_function(message, db):
    subprocess.call(["touch", "monit/heartbeat/orderbook_consumer.txt"])

    ob = json.loads(message)

    assert len(ob.keys()) == 2

    exchange_name = list(set(ob.keys()) - set(['timestamp'])).pop()
    timestamp = ob['timestamp']
    orderbook_data = ob[exchange_name]

    orderbook = Orderbook(
        exchange_name,
        orderbook=orderbook_data,
        timestamp=epoch(timestamp).datetime,
    )

    db.add(orderbook)
    session.commit_mysql_session(db)


def main():
    db = session.get_a_gds_db_mysql_session()

    try:
        orderbook_consumer = QueueConsumer(
            os.environ.get('AMPQ_ADDRESS'),
            orderbook_consumer_function,
            db,
            consts.EXCHANGE,
            consts.EXCHANGE_TYPE,
            consts.ORDERBOOK_BINDING_KEY,
            consts.ORDERBOOK_QUEUE,
        )

        orderbook_consumer.run()
    except KeyboardInterrupt:
        orderbook_consumer.stop()
    except:
        s.captureException()
    finally:
        db.remove()


if __name__ == '__main__':
    main()
