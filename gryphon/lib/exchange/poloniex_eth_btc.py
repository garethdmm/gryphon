# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import decimal
import hashlib
import hmac
import json
import time

from cdecimal import *

from base import *
from exceptions import *
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)


class PoloniexETHBTCExchange(Exchange):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(PoloniexETHBTCExchange, self).__init__(session)
        self.name = u'POLONIEX_ETH_BTC'
        self.friendly_name = u'Poloniex ETH-BTC'
        self.currency = 'BTC'
        self.volume_currency = 'ETH'

