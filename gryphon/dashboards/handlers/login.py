# -*- coding: utf-8 -*-
import logging

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.models.user import User

logger = logging.getLogger(__name__)


class LoginHandler(AdminBaseHandler):
    def get(self):
        if self.get_current_user():
            self.redirect('/')
        else:
            self.render_template('login.html', args={})

    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')

        next = self.get_argument('next', '/')

        user = self.dashboard_db.query(User).filter_by(username=username).first()

        if user:
            if user.password == password:
                self.login_user(user)
                self.redirect(next)
            else:
                self.show_error_message('Incorrect client password.')
                self.redirect('/login')
        else:
            self.show_error_message('Client Does not exist.')
            self.redirect('/login')
