# -*- coding: utf-8 -*-
import logging
import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler

logger = logging.getLogger(__name__)


class LogoutHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        self.logout_user()
        self.redirect('login')

