# -*- coding: utf-8 -*-
import logging
import tornado
import tornado.template
import os
from os.path import dirname, abspath
from tornado.options import define, options
from gryphon.lib.logperf import log_request_perf
import uimodules

# Make filepaths relative to settings.
path = lambda root,*a: os.path.join(root, *a)
ROOT = dirname(dirname(abspath(__file__)))


env_var = os.environ

define("port", default=env_var.get('PORT'), help="run on the given port", type=int)
define("config", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")
define("env", default=env_var['APP_ENV'], help='Environment variable')
define('output_file', default='profile.out')
tornado.options.parse_command_line()

APP_ROOT = env_var['APP_ROOT']
MEDIA_ROOT = path(ROOT, APP_ROOT)
TEMPLATE_ROOT = path(ROOT, APP_ROOT)

# Deployment Configuration
class DeploymentType:
    PRODUCTION = "PRODUCTION"
    LOCAL = "LOCAL"
    STAGING = "STAGING"
    dict = {
        PRODUCTION: 1,
        LOCAL: 2,
        STAGING: 3
    }

if options.env:
    DEPLOYMENT = options.env
else:
    DEPLOYMENT = DeploymentType.LOCAL

settings = {}
settings['log_function']            = log_request_perf
settings['deployment']              = DEPLOYMENT
settings['debug']                   = DEPLOYMENT != DeploymentType.PRODUCTION or options.debug 
settings['xsrf_cookies']            = True
settings['template_loader']         = tornado.template.Loader(TEMPLATE_ROOT)
settings['login_url']               = '/login'
settings['cookie_secret']           = env_var['APP_COOKIE_SECRET']
settings["static_path"]             = os.path.join(os.path.dirname(__file__), "static")
settings['ui_modules']              = uimodules
