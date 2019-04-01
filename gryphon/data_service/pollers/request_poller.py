# -*- coding: utf-8 -*-
import json

from delorean import Delorean
import treq
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.python import log

from gryphon.data_service.pollers.poller import Poller
import gryphon.data_service.util as util


class RequestPoller(Poller):
    @defer.inlineCallbacks
    def start(self):
        self.redis = yield util.setup_redis()
        self.looping_call = LoopingCall(self.get_request)
        self.looping_call.start(self.poll_time)

    def get_request(self):
        agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0"
        d = treq.get(self.url, headers={'user-agent': agent})
        d.addCallback(self.get_response)
        d.addCallback(self.heartbeat)
        d.addErrback(self.log_request_error)

        return d

    def log_request_error(self, error):
        log.err('Error in Request: %s' % str(error))

    def get_response(self, response):
        # Parse the Response and check for errors
        d = treq.content(response)

        # We want to add parse_float=Decimal, but it currently breaks json writing
        # in later code paths
        d.addCallback(json.loads)
        d.addCallback(self.parse_response)
        d.addErrback(self.log_response_error, response)

        return d

    @defer.inlineCallbacks
    def heartbeat(self, response=None):
        yield self.redis.set(self.heartbeat_key, Delorean().epoch)

    def log_response(self, resp_text, label='', *args, **kwargs):
        log.msg(u'%s:%s' % (label, resp_text[:100]))

    def log_response_error(self, error_text, response, *args, **kwargs):
        treq.text_content(response).addCallback(
            self.log_response,
            u'Error in Response from URL:%s %s' % (self.url, error_text),
            log.err,
        )
