# -*- coding: utf-8 -*-
from collections import OrderedDict
import hashlib
import hmac
import time

from cdecimal import *
from delorean import Delorean, parse, epoch

from base import *
from exceptions import *
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)


class BitstampBTCEURExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampBTCEURExchange, self).__init__(session)

        self.name = u'BITSTAMP_BTC_EUR'
        self.friendly_name = u'Bitstamp BTC-EUR'
        self.currency = u'EUR'
        self.volume_currency = 'BTC'

        self.fiat_balance_tolerance = Money('0.0001', 'EUR')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.001', 'BTC')

        if configuration:
            self.configure(configuration)

