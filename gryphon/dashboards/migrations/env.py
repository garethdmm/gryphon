from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine
from logging.config import fileConfig
import logging

logger = logging.getLogger(__name__)


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# for some reason need both of these for imports to work
import os, sys
lib_path = os.path.abspath('.')
sys.path.append(lib_path)

from gryphon.dashboards.models.base import Base
from gryphon.dashboards.models.user import User

target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = os.environ.get('DASHBOARD_DB_CRED')
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    
    engine = create_engine(os.environ.get('DASHBOARD_DB_CRED'))
        
    # engine = engine_from_config(
    #             config.get_section(config.config_ini_section),
    #             prefix='sqlalchemy.',
    #             poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

