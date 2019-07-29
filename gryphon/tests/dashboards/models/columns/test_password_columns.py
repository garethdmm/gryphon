import unittest

import bcrypt
import re
import logging
import sqlalchemy.types as types
from parameterized import parameterized

from .....dashboards.models import Password

# TODO : verify matcher
# @parameterized.expand([
#
# ])
# def test_bcrypt_matcher():
#    pass


class TestPassword(unittest.TestCase):
    @parameterized.expand([
        ("passwd", "passwd"),
        (b"passwd", "passwd"),
    ])
    def test_init_plain(self, plain_passwd, expected_stored_passwd):
        p = Password(plain=plain_passwd)
        assert p._plain == expected_stored_passwd

    @parameterized.expand([
        ("salt", "salt"),
        (b"salt", "salt"),
    ])
    def test_init_plain_salt(self, salt, expected_stored_salt):
        p = Password(salt=salt)
        assert p._salt == expected_stored_salt

    def test_init_value(self):
        raise NotImplementedError

    def test_hashed(self):
        raise NotImplementedError

    @parameterized.expand([
        ("salt",),
        (None,)
    ])
    def test_salt(self, salt):
        p = Password(plain="passwd", salt=salt)
        # testing generation
        assert p.salt == p._salt

        # salt should (probably?) never be None
        assert p.salt is not None

    def test_plain(self):
        raise NotImplementedError

    def test_str(self):
        raise NotImplementedError

    def test_eq(self):
        raise NotImplementedError
