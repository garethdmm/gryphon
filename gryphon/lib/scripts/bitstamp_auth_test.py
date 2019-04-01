"""
This script demonstrates the bitstamp authenticated requests bug that showed up in the
week of 26 March.
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

balance_url = 'https://www.bitstamp.net/api/v2/balance/'


def construct_payload():
    nonce = unicode(int(round(time.time() * 1000)))
    message = nonce + CLIENT_ID + API_KEY
    sig = hmac.new(SECRET, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

    payload = {
        'nonce': nonce,
        'key': API_KEY,
        'signature': sig,
    }

    return payload


def test_response(response, test_name):
    print 'Response: %s' % str(response)[:50]

    try:
        assert('btc_available' in response)
        print '%s succeeded!' % test_name
    except Exception as e:
        print '%s: %s' % (test_name, str(e))


def requests_dot_post():
    """
    This just makes a single request.post call to see if it works.
    """

    print "Trying requests.post"

    payload = construct_payload()

    result = requests.post(balance_url, data=payload).text

    test_response(result, 'requests.post')


def session_post(session=None, clear_cookies=None, adaptor=None, cookie_jar=None):
    """
    This function makes a single Session().post call, either with a new session or an
    existing session. It also takes arguments for specific SSLAdapters or CookieJar
    types.
    """
    if session is None:
        print "Trying with a new session"
        session = requests.Session()

        if adaptor is not None:
            session.mount('https://', adaptor)

        if cookie_jar is not None:
            session.cookies = cookie_jar
    else:
        print "Trying with an extant session"

        if clear_cookies is True:
            print "Clearing the session's cookies"
            session.cookies.clear()

    payload = construct_payload()

    result = session.post(balance_url, payload).text

    test_response(result)

    return session


def try_different_adaptors():
    """
    This method didn't return any positive results but it was work a try. We were
    looking to see if using different SSLAdapters with the session object made a
    difference. It certainly has different behaviour on different platforms but did
    not fix the issue.
    """

    from requests_toolbelt import SSLAdapter
    import ssl

    ssl3 = SSLAdapter(ssl.PROTOCOL_SSLv23)
    tls1 = SSLAdapter(ssl.PROTOCOL_TLSv1)
    tls11 = SSLAdapter(ssl.PROTOCOL_TLSv1_1)

    print 'TLSv1'
    session = session_post(adaptor=tls1)
    session_post(session=session)

    print 'TLSv1'
    session = session_post(adaptor=tls11)
    session_post(session=session)

    print 'SSLv3'
    session = session_post(adaptor=ssl3)
    session_post(session=session)


def try_two_simple_requests():
    """
    This test demonstrates that doing two requests.post calls to the same endpoint
    works fine.
    """

    requests_dot_post()
    requests_dot_post()


def try_two_requests_with_one_session():
    """
    This test demonstrates that the second authenticated request made with a session
    object fails.
    """

    session = session_post()
    session_post(session=session)


def try_two_requests_with_one_session_then_clear_cookies():
    """
    This test demonstrates that clearing the cookies of the Session() object makes
    subsequent requests possible.
    """

    session = session_post()
    session_post(session=session)
    session_post(session=session, clear_cookies=True)


def try_forgetful_cookie_jar():
    """
    Tests whether using ForgetfulCookieJar with requests.Session() is a viable
    workaround.
    """
    from requests_toolbelt.cookies.forgetful import ForgetfulCookieJar

    jar = ForgetfulCookieJar()

    session = session_post(cookie_jar=jar)

    session_post(session=session)
    session_post(session=session)
    session_post(session=session)


def try_forgetful_futures():
    """
    Tests the workaround using ForgetfulCookieJar with requests_futures.
    """

    from requests_toolbelt.cookies.forgetful import ForgetfulCookieJar
    from requests_futures.sessions import FuturesSession

    session = FuturesSession()
    jar = ForgetfulCookieJar()
    session.cookies = jar

    payload1 = construct_payload()
    req1 = session.post(balance_url, payload1)
    resp1 = req1.result().text

    payload2 = construct_payload()
    req2 = session.post(balance_url, payload2)
    resp2 = req2.result().text

    test_response(resp1, 'Forgetful Futures req1')
    test_response(resp2, 'Forgetful Futures req2')

    return session


try_forgetful_futures()

