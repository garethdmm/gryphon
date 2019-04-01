"""
Prepared by Gareth MacLeod, 3 April 2018.

This demonstrates that python 2.7 is having series issues with authenticated requests 
to the bitstamp API. This script fails on fresh installs of Ubuntu 14.04 LTS and 16 LTS.

The deepest I've gotten into this bug is this: the requests.Session() object can make
a single successful authenticated request to the API, but then any subsequent
authenticated request fails.

HOWEVER: If you clear the cookies of that session after each request, it then succeeds.
This might sound like a hacky, possibly viable solution, but I suspect that clearing
the cookies actually negates all the performance benefits of keeping a single connection
to bitstamp open.

The python environent is this:

asn1crypto==0.24.0
certifi==2018.1.18
cffi==1.11.5
chardet==3.0.4
click==6.7
cryptography==2.2.2
enum34==1.1.6
idna==2.6
ipaddress==1.0.19
ordereddict==1.1
pycparser==2.18
pyOpenSSL==17.5.0
python-dotenv==0.3.0
requests==2.18.4
six==1.11.0
urllib3==1.22

OpenSSL version 1.0.2g.

You can construct this environment just by setting up a fresh Ubuntu 14/16 install, then
running

sudo apt update
sudo apt install python python-pip
pip install requests[security]

Make sure you have yoru bitstamp credentials in a .env file in the directory you are
running from.
"""

import requests
import hmac
import time
import hashlib
import time

import dotenv
import os
import os.path

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)


API_KEY = str(os.environ['BITSTAMP_ETH_EUR_API_KEY'])
SECRET = str(os.environ['BITSTAMP_ETH_EUR_API_SECRET'])
CLIENT_ID = str(os.environ['BITSTAMP_ETH_EUR_CLIENT_ID'])

API_BALANCE_URL = 'https://www.bitstamp.net/api/v2/balance/'


def requests_dot_post():
    print '---'
    print "Trying requests.post"

    nonce = unicode(int(round(time.time() * 1000)))
    message = nonce + CLIENT_ID + API_KEY
    sig = hmac.new(SECRET, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

    payload = {
        'nonce': nonce,
        'key': API_KEY,
        'signature': sig,
    }

    result = requests.post(API_BALANCE_URL, data=payload).text

    print 'Response from bitstamp: %s' % result[:50]

    try:
        assert('btc_available' in result)
        print 'requests.post succeeded!'
    except Exception as e:
        print 'requests.post failed: %s' % str(e)


def session_post(session=None, clear_cookies=None):
    print '---'

    if session is None:
        print "Trying with a new session"

        session = requests.Session()
    else:
        print "Trying with an extant session"

        if clear_cookies is True:
            print "Clearing the session's cookies"
            session.cookies.clear()

    nonce = unicode(int(round(time.time() * 1000)))
    message = nonce + CLIENT_ID + API_KEY
    sig = hmac.new(SECRET, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

    payload = {
        'nonce': nonce,
        'key': API_KEY,
        'signature': sig,
    }

    result = session.post(API_BALANCE_URL, payload).text

    print 'Response from bitstamp: %s' % result[:50]

    try:
        assert('btc_available' in result)
        print 'Session succeeded!'
    except Exception as e:
        print 'Session failed: %s' % str(e)

    return session


requests_dot_post()
requests_dot_post()
session = session_post()
session_post(session=session)
session_post(session=session, clear_cookies=True)


