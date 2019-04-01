import os
from sqlalchemy import UnicodeText, TypeDecorator
from gryphon.lib.encrypt import *

try:
    DB_ENCRYPT_KEY = os.environ['DB_ENCRYPT_KEY']
except:
    raise Exception("""Requires environment variables: DB_ENCRYPT_KEY""")

class EncryptedUnicodeText(TypeDecorator):
    impl = UnicodeText

    def process_bind_param(self, value, dialect):
        secret_key = DB_ENCRYPT_KEY
        if value:
            return encrypt(value, secret_key)
        else:
            return value

    def process_result_value(self, value, dialect):
        secret_key = DB_ENCRYPT_KEY
        if value:
            return decrypt(value, secret_key)
        else:
            return value
