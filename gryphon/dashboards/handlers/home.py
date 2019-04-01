# -*- coding: utf-8 -*-
import tornado.web

from admin_base import AdminBaseHandler


class HomeHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render_template('home.html', args={})
