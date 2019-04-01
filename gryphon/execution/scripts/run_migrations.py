"""
This script allows pip users to run migrations on the databases they use with gryphon.
Gryphon uses alembic to manage migrations.

Usage:
    gryphon-execute script run_migrations
        --database [GDS | TRADING | DASHBOARD]
"""

import pyximport; pyximport.install()

import logging
import os
from pkg_resources import resource_filename

from alembic.config import Config
from alembic import command

from gryphon.lib import session

logger = logging.getLogger(__name__)


GDS_CONFIG_RELATIVE_PATH = 'data_service/alembic.ini'
DASHBOARD_CONFIG_RELATIVE_PATH = 'dashboards/alembic.ini'
TRADING_CONFIG_RELATIVE_PATH = 'execution/alembic.ini'

PACKAGE_NAME = 'gryphon'

GDS_DB_NAME = 'gds'
TRADING_DB_NAME = 'trading'
DASHBOARD_DB_NAME = 'dashboard'
DATABASE_NAMES = [GDS_DB_NAME, TRADING_DB_NAME, DASHBOARD_DB_NAME]

NO_EXECUTE_MESSAGE = 'Not running migration because execute == False'

UNKNOWN_DB_MESSAGE = 'There is no database %s associated with the gryphon-framework.'


def run_migrations(target_db):
    location = None

    if target_db == GDS_DB_NAME:
        location = resource_filename(PACKAGE_NAME, GDS_CONFIG_RELATIVE_PATH)
    elif target_db == DASHBOARD_DB_NAME:
        location = resource_filename(PACKAGE_NAME, DASHBOARD_CONFIG_RELATIVE_PATH)
    elif target_db == TRADING_DB_NAME:
        location = resource_filename(PACKAGE_NAME, TRADING_CONFIG_RELATIVE_PATH)
    
    alembic_cfg = Config(location)
    command.upgrade(alembic_cfg, 'head')


def main(script_arguments, execute):
    target_db = script_arguments['database']

    target_db = target_db.lower()

    if target_db in DATABASE_NAMES:
        logger.info('Migrating the %s database' % target_db)
    else:
        logger.info(UNKNOWN_DB_MESSAGE % target_db)
        return

    if execute is True:
        run_migrations(target_db)
    else:
        logger.info('Not running migration because execute == False')

