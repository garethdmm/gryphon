"""
This is a minimal script that demonstrates authentication on itbit. This is useful for
debugging if you ever run into issues with authenticating on itbit.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib
import os
import requests


USER_ID = os.environ['ITBIT_USER_ID']
API_KEY = os.environ['ITBIT_API_KEY']
API_SECRET = os.environ['ITBIT_API_SECRET'].encode('utf-8')
WALLET_ID = os.environ['ITBIT_WALLET_ID']


def main(script_arguments, execute):
    request_args = {}

    request_args['data'] = ''
    timestamp = int(round(time.time() * 1000))
    nonce = 1
    url = '/wallets/%s' % WALLET_ID
    req_method = 'GET'
    json_body = ''

    message = json.dumps([
        req_method.upper(),
        url,
        json_body,
        str(nonce),
        str(timestamp)
        ], separators=(',', ':'),
    )

    sha256_hash = hashlib.sha256()
    nonced_message = str(nonce) + message
    sha256_hash.update(nonced_message)
    hash_digest = sha256_hash.digest()

    msg_to_hmac = url.encode('utf8') + hash_digest
    hmac_digest = hmac.new(API_SECRET, msg_to_hmac, hashlib.sha512).digest()

    sig = base64.b64encode(hmac_digest)

    headers = request_args['headers'] = {}

    headers['Authorization'] = API_KEY + ':' + sig
    headers['X-Auth-Timestamp'] = timestamp
    headers['X-Auth-Nonce'] = nonce
    headers['Content-Type'] = 'application/json'

    # Make the request

    full_url = 'https://api.itbit.com/v1' + url

    print requests.get(full_url, data=request_args).text

