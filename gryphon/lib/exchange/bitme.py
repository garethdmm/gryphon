# -*- coding: utf-8 -*-
import time
import os
import datetime
import requests
import hmac
import urllib
import hashlib
import base64
import json
import math
from urllib import urlencode
from collections import OrderedDict
from delorean import Delorean, parse

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money
from base import *
from exceptions import *
from exchange_order import Order
from gryphon.lib.models.exchange import Balance

from cdecimal import *
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class BitmeExchange(Exchange):
    def __init__(self, session=None):
        super(BitmeExchange, self).__init__(session)
        self.name = u'BITME'
        self.friendly_name = u'bitme'
        self.base_url = 'https://bitme.com/rest'
        self.currency = "USD"
        self.fee = Decimal("0")
        self.bid_string = "BID"
        self.ask_string = "ASK"
