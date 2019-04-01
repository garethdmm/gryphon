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
from delorean import Delorean, parse
import urllib
from collections import OrderedDict

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money
from base import *
from exceptions import *
from exchange_order import Order
from gryphon.lib.models.exchange import Balance
from gryphon.lib.models.datum import DatumRecorder

from cdecimal import *
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class ButtercoinExchange(Exchange):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(ButtercoinExchange, self).__init__(session)
        self.name = u'BUTTERCOIN'
        self.friendly_name = u'Buttercoin'
        self.base_url = 'https://api.buttercoin.com/v1'
        self.currency = "USD"
        self.fee = Decimal("0")
        self.bid_string = "buy"
        self.ask_string = "sell"
        self.use_cached_orderbook = use_cached_orderbook
