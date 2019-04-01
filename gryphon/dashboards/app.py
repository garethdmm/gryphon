import dotenv
import logging
import os

import tornado.httpserver
import tornado.ioloop
from tornado.options import options
import tornado.web
import tornadotoad

# I believe setting the environment needs to happen first so any gryphon imports already
# have access.
from gryphon.lib import environment
environment.load_environment_variables()

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

from gryphon.dashboards.routes import url_patterns
from gryphon.dashboards.settings import settings
from gryphon.lib import configuration
from gryphon.lib import session

logger = logging.getLogger(__name__)

options.port = 8080

if 'APP_PORT' in os.environ:
    options.port = int(os.environ['APP_PORT'])

GDS_ERROR = """\
Could not find a gds credential, orderbook and other dashboards won't be operational\
"""


class PentecostApp(tornado.web.Application):
    """
    The main init for the application. Starts the application, defines the db.
    """
    def __init__(self):
        tornado.web.Application.__init__(self, url_patterns, **settings)

        self.dashboard_db = session.get_a_dashboard_db_mysql_session()
        self.trading_db = session.get_a_trading_db_mysql_session()

        try:
            self.gds_db = session.get_a_gds_db_mysql_session()
        except KeyError as e:
            logger.info(GDS_ERROR)
            self.gds_db = None

        self.configuration = configuration.read_config_from_file('dashboards.conf')
        

def main():
    tornadotoad.register(
      api_key=os.environ.get('AIRBRAKE_API_KEY'),
      environment=os.environ.get('APP_ENV'),
    )

    app = PentecostApp() 
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
