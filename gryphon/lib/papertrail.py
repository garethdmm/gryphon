# -*- coding: utf-8 -*-
import requests
import os

try:
    PAPERTRAIL_TOKEN = os.environ['PAPERTRAIL_API_TOKEN']
except:
    raise Exception("""Requires environment variables: PAPERTRAIL_API_TOKEN""")

class Papertrail(object):
    @staticmethod
    def get_logs(query):
        """
        curl -v -H "X-Papertrail-Token: abc123" "https://papertrailapp.com/api/v1/events/search.json?q='Critical error'"
        """
        search_query = "%s" % query
        url = 'https://papertrailapp.com/api/v1/events/search.json?q=%s' % search_query
        headers = {'X-Papertrail-Token':PAPERTRAIL_TOKEN}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json()
        else:
            return {}

