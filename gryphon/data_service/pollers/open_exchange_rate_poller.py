# -*- coding: utf-8 -*-
import json
import os

from delorean import Delorean
from twisted.internet import defer
from twisted.python import log

from gryphon.data_service.pollers.request_poller import RequestPoller


class OpenExchangeRatePoller(RequestPoller):
    def __init__(self):
        app_id = os.environ['EXCHANGE_RATE_APP_ID']
        self.url = 'https://openexchangerates.org/api/latest.json?app_id=%s&show_alternative=true' % app_id
        self.poll_time = 60
        self.heartbeat_key = 'open_exchange_rate_poller_heartbeat'

    @defer.inlineCallbacks
    def parse_response(self, resp_obj):
        ts = Delorean().epoch

        exchange_rate_string = json.dumps({
            'timestamp': ts,
            'exchange_rates': resp_obj,
        })

        if resp_obj:
            yield self.redis.set('emerald_havoc_exchange_rates', exchange_rate_string)

            log.msg('[Exchange Rate] Successful @ %s' % ts)
        else:
            log.msg('[Exchange Rage] Unsuccessful @ %s' % ts)

