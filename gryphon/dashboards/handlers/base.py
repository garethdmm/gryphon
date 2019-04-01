# -*- coding: utf-8 -*-
import logging
import os
import traceback

import sqlalchemy.exc
import tornado.web
from tornadotoad import api
from tornadotoad import my

from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook

logger = logging.getLogger(__name__)

P3P_POLICY = u"""\
CP="Like Facebook, This App does not have a P3P policy -Learn why: http://fb.me/p3p\
"""


class BaseHandler(tornado.web.RequestHandler):
    """
    A class to collect common handler methods - all other handlers should subclass this
    one.
    """
    @property
    def dashboard_db(self):
        return self.application.dashboard_db

    @property
    def trading_db(self):
        return self.application.trading_db

    @property
    def gds_db(self):
        return self.application.gds_db

    @property
    def configuration(self):
        return self.application.configuration

    def send_error(self, status_code, **kwargs):
        if status_code == 403 and not my.log_403:
            return super(BaseHandler, self).send_error(status_code, **kwargs)

        if status_code == 404 and not my.log_404:
            return super(BaseHandler, self).send_error(status_code, **kwargs)

        if status_code == 405 and not my.log_405:
            return super(BaseHandler, self).send_error(status_code, **kwargs)

        tornado_toad = api.TornadoToad()
        exception = kwargs.get('exc_info')

        if exception:
            formatted_arguments = {}

            for key in self.request.arguments.keys():
                formatted_arguments[key] = u','.join(self.request.arguments[key])

            request_data = {
                'url': self.request.full_url(),
                'component': self.__class__.__name__,
                'cgi-data': self.request.headers,
                'params': formatted_arguments,
            }

            tornado_toad.post_notice(exception, request=request_data)

        return super(BaseHandler, self).send_error(status_code, **kwargs)

    def commit_session(self):
        try:
            self.dashboard_db.commit()
        except Exception as e:
            self.dashboard_db.rollback()

            logger.critical(u'BASE - commit needed to roll back.')
            logger.critical(
                u'Transaction needed to be rolled back because of: \n %s' % (
                traceback.format_exc(),
            ))

    def prepare(self):
        if (os.environ.get('APP_ENV') == 'PRODUCTION'
                and self.request.headers.get('X-Forwarded-Proto') != 'https'):
            old_url = self.request.full_url()
            new_url = old_url.replace('http://', 'https://')
            self.redirect(new_url, permanent=True)

            return

        p3p = P3P_POLICY
        self.add_header('Accept-Charset', u'utf-8')
        self.add_header('X-Frame-Options', u'deny')
        self.set_header('P3P', p3p)

    @property
    def should_recalculate_stored_results(self):
        return self.get_argument('recalculate', None) is not None

    def is_gds_connection_active(self):
        """
        Simple function to test if we have a working connection to a GDS instance so
        we don't error out accidentally.
        """
        if self.gds_db is None:
            return False

        try:
            self.gds_db.query(Orderbook.orderbook_id).first()
        except sqlalchemy.exc.OperationalError as error:
            return False

        return True

    def on_finish(self):
        try:
            self.dashboard_db.commit()
        except Exception:
            self.dashboard_db.rollback()

            logger.critical(
                u'Transaction needed to be rolled back because of: \n %s' % (
                traceback.format_exc(),
            ))
        finally:
            self.dashboard_db.remove()

        try:
            self.trading_db.commit()
        except Exception:
            self.trading_db.rollback()

            logger.critical(
                u'Transaction needed to be rolled back because of: \n %s' % (
                traceback.format_exc(),
            ))
        finally:
            self.trading_db.remove()

        if self.gds_db is not None:
            try:
                self.gds_db.commit()
            except Exception:
                self.gds_db.rollback()

                logger.critical(
                    u'TC Transaction needed to be rolled back because of: \n %s' % (
                    traceback.format_exc(),
                ))
            finally:
                self.gds_db.remove()
