import json
import os

import requests

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

# you probably haven't heard of this exception before
class SlackerException(Exception):
    pass


class Slacker(object):
    def __init__(self, channel, username, icon_url=None, icon_emoji=None, link_names=True):
        self.channel = channel
        self.username = username
        self.icon_url = icon_url
        self.icon_emoji = icon_emoji
        self.link_names = link_names

        self.url = os.environ['SLACK_WEBHOOK_URL']

    def notify(self, message):
        payload = {
            'channel': self.channel,
            'username': self.username,
            'text': message,
        }

        if self.icon_url:
            payload['icon_url'] = self.icon_url

        if self.icon_emoji:
            payload['icon_emoji'] = self.icon_emoji

        if self.link_names is not None:
            payload['link_names'] = self.link_names

        json_payload = json.dumps(payload)

        r = requests.post(self.url, data=json_payload)
        if not r.ok:
            raise SlackerException(r.text)
