# -*- coding: utf-8 -*-
import logging
import traceback

import tornado.web

from gryphon.dashboards.handlers.base import BaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.dashboards.models.user import User
from gryphon.dashboards.util.exchanges import load_exchange_names
from gryphon.lib.exchange import exchange_factory
from gryphon.dashboards.handlers.strategies.builtin_configs import BUILTIN_STRAT_CONFIGS

logger = logging.getLogger(__name__)


class AdminBaseHandler(BaseHandler):
    """
    A class to collect common handler methods - all other handlers should subclass this
    one.
    """
    def write_error(self, status_code, **kwargs):
        """
        Override to implement custom error pages.
        """
        if 'exc_info' in kwargs and status_code not in [403, 404, 405]:
            exc_info = kwargs.get('exc_info')

            error_readout = [
                unicode(line, 'utf8') for line in traceback.format_exception(*exc_info)
            ]

            logger.critical(u''.join(error_readout))

        self.render_template('error.html', args={})

    def get_current_user(self):
        if not hasattr(self, 'dashboard_db'):
            return None

        if not hasattr(self, '_current_user'):
            self._current_user = self.dashboard_db.query(User)\
                .filter_by(unique_id=self.get_secure_cookie('user'))\
                .first()

        return self._current_user

    def get_secure_cookie(self, name, include_name=True, value=None):
        cookie_value = super(AdminBaseHandler, self).get_secure_cookie(name)
        return unicode(cookie_value or '', 'utf8')

    def show_error_message(self, message):
        self.set_secure_cookie('error_message', message)

    def show_message(self, message):
        self.set_secure_cookie('message', message)

    def login_user(self, user):
        self._current_user = user
        self.set_secure_cookie('user', user.unique_id)

    def logout_user(self):
        self._current_user = None
        self.clear_cookie('user')

    def render_template(self, template, **kwargs):
        # Grab the cookie messages.
        current_user = self.get_current_user()
        cookie_message = self.get_secure_cookie('message')
        error_message = self.get_secure_cookie('error_message')
        self.set_secure_cookie('message', u'')
        self.set_secure_cookie('error_message', u'')

        kwargs.update({
            'user': current_user,
            'error_message': error_message,
            'message': cookie_message,
            'xsrf_token': self.xsrf_token,
        })

        exchange_names_map = load_exchange_names(self.trading_db)
        datum_links = self.datum_links(exchange_names_map)

        if 'args' not in kwargs:
            kwargs['args'] = {}

        custom_strategies = {
            key: val for key, val in self.configuration['strategies'].items()
            if key not in BUILTIN_STRAT_CONFIGS
        }

        kwargs['args'].update({
            'exchanges': exchange_names_map,
            'bank_account_keys': exchange_factory.BANK_ACCOUNT_KEYS,
            'datum_links': datum_links,
            'custom_strategies': custom_strategies,
        })

        if isinstance(self, StartAndEndTimeMixin):
            start_time, end_time = self.get_start_time_and_end_time()

            kwargs['args']['start_end_widget'] = {
                'start_time': start_time,
                'end_time': end_time,
            }

        template = 'templates/%s' % template

        return self.render(template, **kwargs)

    def datum_links(self, exchange_names_map):
        exchange_keys = [k.upper() for k in exchange_names_map]

        spread_datum_keys = []
        ob_delay_datum_keys = []

        for exchange_key in exchange_keys:
            spread_datum_keys.append('%s_NATIVE_FUNDAMENTAL_VALUE' % exchange_key)
            ob_delay_datum_keys.append('%s_ORDERBOOK_DELAY' % exchange_key)

        spread_url = '/gryphon-fury/datum/%s' % '~'.join(spread_datum_keys)
        ob_delay_url = '/gryphon-fury/datum/%s' % '~'.join(ob_delay_datum_keys)

        links = [
            ['Spreads', spread_url],
            ['Orderbook Delays', ob_delay_url],
        ]

        return links


class Handler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self):
        start_time, end_time = self.get_start_time_and_end_time()
