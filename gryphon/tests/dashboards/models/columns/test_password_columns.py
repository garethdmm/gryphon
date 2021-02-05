import unittest

import bcrypt
import re
import logging
import sqlalchemy.types as types
from parameterized import parameterized

from .....dashboards.models.columns.password_column import bcrypt_matcher
from .....dashboards.models import Password


# parameterized test values are currently basic for illustration purposes
# TODO : types + hypothesis to test wide range of values.


@parameterized.expand([
    (r'$2a$12$sssssssssssssssssssssshhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh', True),
    (b'$2a$12$sssssssssssssssssssssshhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh', True),
    (u'$2a$12$sssssssssssssssssssssshhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh', True),
    (r'sh', False),
    (r's', False),
    (r'h', False),
])
def test_bcrypt_matcher(value, should_match):
    m= bcrypt_matcher(value)
    if not should_match:
        assert m is None
    else:  # should match
        assert m


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

    @parameterized.expand([
        ('saltsaltsaltsaltsalts', 'hashhashhashhashhashhashhashhas')
    ])
    def test_init_value(self, salt, hash):

        val = '$2a$12$' + salt + hash
        p = Password(val)
        assert p._salt == salt, p._salt == salt
        assert p._hashed == hash, p._hashed == hash

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

    @parameterized.expand([
        ("passwd",),
    ])
    def test_plain(self, plain_passwd):
        p = Password(plain=plain_passwd)
        assert p.plain == plain_passwd

    @parameterized.expand([
        ("passwd",),
    ])
    def test_str(self, plain_passwd):
        p = Password(plain=plain_passwd)
        assert str(p) == p.hashed

    @parameterized.expand([
        ("passwd",),
        (b"passwd",),
    ])
    def test_eq_true(self, plain_passwd):
        p1 = Password(plain=plain_passwd)
        # generate hash value
        assert p1.hashed
        # copy will copy the hashed value
        import copy
        p2 = copy.copy(p1)
        assert p1 == p2

    @parameterized.expand([
        ("passwd"),
        (b"passwd"),
    ])
    def test_eq_false(self, plain_passwd):
        pd1 = Password(plain=plain_passwd)
        pd2 = Password(plain=plain_passwd)
        assert pd1 != pd2