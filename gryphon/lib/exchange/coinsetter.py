# -*- coding: utf-8 -*-
import base64
import datetime
import hashlib
import hmac
import json
import math
import os
import requests
import time
import urllib
import decimal
from cdecimal import *
from collections import OrderedDict
from delorean import Delorean, parse
from urllib import urlencode

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.base import *
from gryphon.lib.exchange.exceptions import *
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

logger = get_logger(__name__)


class CoinsetterExchange(Exchange):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(CoinsetterExchange, self).__init__(session)
        self.name = u'COINSETTER'
        self.friendly_name = u'Coinsetter'
        self.base_url = 'https://api.coinsetter.com/v1'
        self.currency = "USD"
        self.fee = Decimal("0.002")
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.bid_string = "BUY"
        self.ask_string = "SELL"
        self.use_cached_orderbook = use_cached_orderbook
