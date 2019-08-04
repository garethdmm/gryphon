# -*- coding: utf-8 -*-
from __future__ import absolute_import
import tornado.web

from .admin_base import AdminBaseHandler


class HomeHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render_template('home.html', args={})
