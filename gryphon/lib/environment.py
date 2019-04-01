"""
Just a small module to centralize our handling of .env files in gryphon. Currently all
our executables look for a file named '.env' in the current working directory. This
could be made more sophisticated in the future, e.g., looking for ~/.gryphon/.env first,
and allowing a cwd .env file to override. Lots of options.
"""

import os
from os.path import join

from dotenv import load_dotenv


def load_environment_variables():
    """
    Presently, this function looks for a .env file in the current directory and loads
    the variables present therin into os.environ.
    """
    dotenv_path = join(os.getcwd(), '.env')
    load_dotenv(dotenv_path)
