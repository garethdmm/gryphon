"""
This scripts creates a username/password credential in the dashboard database. We do
this through the command line to ensure that plaintext passwords are not stored in the
database.

Usage: gryphon-execute script create_dashboard_user [--execute]
"""

import getpass
import termcolor as tc
import os

from gryphon.lib import session
from gryphon.dashboards.models.user import User
from gryphon.dashboards.models.columns.password_column import Password


WARNING_MESSAGE = """
You are about to create a database user for the gryphon dashboard server.
This user will be able to access all of your dashboards, view trading returns, \
download ledger information, and generally know nearly everything about your trading \
business.
Are you sure you want to continue?"""

WARNING_PROMPT = """('y' to continue creating a user)):"""

EXIT_MESSAGE = """Ok. Exiting with no actions taken."""

CONTINUE_MESSAGE = """Ok, let's continue"""

ENTER_USERNAME_MESSAGE = """Enter your desired username: """

ENTER_PASSWORD_MESSAGE = """Enter your desired password: """

SUCCESS_NO_EXECUTE_MESSAGE = """\
Successfully created user object, but not committing because you did not add the \
--execute flag at the command line.
"""

SUCCESS_MESSAGE = """\
Success! You should be able to log in with the new credentials now.'\
"""


def main(script_arguments, execute):
    print tc.colored(WARNING_MESSAGE, 'red')
    informed_consent = raw_input(WARNING_PROMPT)

    if informed_consent != 'y':
        print EXIT_MESSAGE
        return
    else:
        print CONTINUE_MESSAGE

    dashboard_db = session.get_a_dashboard_db_mysql_session()

    username = raw_input(ENTER_USERNAME_MESSAGE)
    password_text = getpass.getpass(ENTER_PASSWORD_MESSAGE)

    password = Password(plain=password_text)
    
    user = User(username, password)

    if execute is True:
        dashboard_db.add(user)
        dashboard_db.commit()

        print tc.colored(SUCCESS_MESSAGE, 'green')
    else:
        print SUCCESS_NO_EXECUTE_MESSAGE
     
