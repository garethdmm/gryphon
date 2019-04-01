# -*- coding: utf-8 -*-

from gryphon.lib.logger import get_logger
logger = get_logger(__name__)
import requests
import time

class RetryRequest(object):
    
    @staticmethod
    def get(url, retry_attempts=0, **kwargs):
         RetryRequest._req('GET', url, retry_attempts, **kwargs)
         
    @staticmethod
    def post(url, retry_attempts=0, **kwargs):
        RetryRequest._req('POST', url, retry_attempts, **kwargs)
                
    @staticmethod
    def _req(http_method, url, retry_attempts=0, **kwargs):
        attempts = 0
        while True:
            try:
                if http_method == 'POST':
                    r = requests.post(url, **kwargs)
                elif http_method == 'GET':
                    r = requests.get(url, **kwargs)
                else:
                    raise NotImplementedError('HTTP METHOD does not exist')
                return r
            except Exception as e:
                attempts += 1
                if attempts > retry_attempts:
                    raise e
                else:
                    logger.info(u'[RETRY REQUEST] - This time failed.  Trying Again.')
                    time.sleep(0.1)
