import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler


class NotFoundHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render_template('404.html')
