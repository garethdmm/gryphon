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
from collections import defaultdict, OrderedDict
import copy
from delorean import Delorean, parse, epoch

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money
from exchange_order import Order
from base import *
from exceptions import *
from gryphon.lib.models.exchange import Balance

from cdecimal import *
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class CaVirtexExchange(Exchange):
    def __init__(self, session=None, currency=u"CAD", use_cached_orderbook=False):
        super(CaVirtexExchange, self).__init__(session)
        self.name = u'CAVIRTEX'
        self.friendly_name = u'CaVirtex'
        self.base_url = 'https://www.cavirtex.com/api2'
        self.currency = currency
        self.fee = Decimal("0.00") # special 2-month zero-fee deal
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.withdrawal_fee = Money("0.001", "BTC")
        self.bid_string = "buy"
        self.ask_string = "sell"
        self.use_cached_orderbook = use_cached_orderbook
