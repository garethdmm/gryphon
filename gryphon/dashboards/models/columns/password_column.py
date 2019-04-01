import bcrypt
import re
import logging
import sqlalchemy.types as types

bcrypt_matcher = re.compile(r'\A(?P<salt>\$2a?\$\d{2}\$[./0-9a-zA-Z]{22})(?P<hashed>[./0-9a-zA-Z]{31})\Z').match

class Password(object):
    DIFFICULTY = 12

    def __init__(self, value=None, **kwargs):
        self._hashed = kwargs.get('hashed', None)
        self._plain = kwargs.get('plain', None)
        self._salt = kwargs.get('salt', None)

        if self._plain:
            self._plain = self._plain.encode('utf-8')

        if self._salt:
            self._salt = self._salt.encode('utf-8')

        if value:
            match = bcrypt_matcher(value)

            if match:
                self._salt = match.group('salt')
                self._hashed = match.group('hashed')
            else:
                self._plain = value

    def __eq__(self, other):
        if isinstance(other, Password):
            return self.hashed == other.hashed
        else:
            return self.__eq__(Password(plain=other, salt=self.salt))

    @property
    def hashed(self):
        if not self._hashed:
            self._hashed = bcrypt.hashpw(self.plain, self.salt)
        return self._hashed

    @property
    def salt(self):
        if not self._salt:
            if self._hashed:
                self._salt = self._hashed[:30]
            else:
                self._salt = bcrypt.gensalt(log_rounds=self.DIFFICULTY)
        return self._salt

    @property
    def plain(self):
        return self._plain

    def __str__(self):
        return self.hashed

class PasswordColumn(types.TypeDecorator):
    impl = types.String(100)

    def process_bind_param(self, value, dialect):
        return value.hashed

    def process_result_value(self, value, dialect):
        return Password(hashed=value)

