import json

from delorean import Delorean
from twisted.internet import defer

import gryphon.data_service.consts as consts
from gryphon.data_service.pollers.request_poller import RequestPoller
import gryphon.data_service.util as util


class VolumePoller(RequestPoller):
    @property
    def volume_key(self):
        return '%s_volume' % self.exchange_name.lower()

    @property
    def heartbeat_key(self):
        return '%s_volume_heartbeat' % self.exchange_name.lower()

    @defer.inlineCallbacks
    def start(self):
        self.poll_time = 55
        binding_key = '%s.exchange_volume.tinker' % self.exchange_name.lower()

        self.producer = yield util.setup_producer(
            consts.EXCHANGE_VOLUME_QUEUE,
            binding_key,
        )

        super(VolumePoller, self).start()

    def parse_volume_json(self, volume_json):
        """ Parses incoming json from exchange into a string number """
        raise NotImplementedError

    def parse_response(self, response):
        """ Parses the volume response from the exchange. """

        volume = self.parse_volume_json(response)
        raw_timestamp = Delorean().epoch

        if volume and self.producer:
            new_volume = {
                'timestamp': raw_timestamp,
                'exchange_name': self.exchange_name,
                'volume': volume,
            }

            new_volume_string = json.dumps(new_volume, ensure_ascii=False)
            self.producer.publish_message(new_volume_string)
