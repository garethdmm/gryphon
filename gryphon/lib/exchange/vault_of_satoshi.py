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
from cdecimal import *
from delorean import Delorean
from collections import OrderedDict

from gryphon.lib.money import Money
from gryphon.lib.models.datum import DatumRecorder
from exchange_order import Order
from gryphon.lib.exchange.consts import Consts
from base import *
from exceptions import *
from gryphon.lib.models.exchange import Balance

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class VaultOfSatoshiExchange(Exchange):
    def __init__(self, session=None, currency=u"CAD", use_cached_orderbook=False):
        super(VaultOfSatoshiExchange, self).__init__(session)
        self.name = u'VAULTOFSATOSHI'
        self.friendly_name = u'Vault of Satoshi'
        self.base_url = 'https://api.vaultofsatoshi.com'
        self.currency = currency
        self.fee = Decimal("0") # assuming $99 unlimited account
        self.withdrawal_fee = Money("0.0005", "BTC")
        self.bid_string = "bid"
        self.ask_string = "ask"
        self.use_cached_orderbook = use_cached_orderbook
