import json
import os
import requests

from cdecimal import *
from delorean import Delorean, epoch

from gryphon.lib.session import get_a_redis_connection
from gryphon.lib.logger import get_logger
from gryphon.lib.cache import cache_me

logger = get_logger(__name__)


MISSING_ENV_VAR_ERROR = """Requires environment variables: EXCHANGE_RATE_APP_ID"""


class USDCurrencyConverter(object):
    @staticmethod
    def get_rates_from_redis():
        exchange_rate_age_threshold = 60*60 # 1hr
        
        try:
            r = get_a_redis_connection()
            exchange_rates_string = r.get('emerald_havoc_exchange_rates')
            logger.info(exchange_rates_string[:100])

            if exchange_rates_string:
                exchange_rates_dict = json.loads(
                    exchange_rates_string,
                    parse_float=Decimal,
                )

                timestamp = exchange_rates_dict['timestamp']
                now_timestamp = Delorean().epoch

                if timestamp + exchange_rate_age_threshold > now_timestamp:
                    return exchange_rates_dict['exchange_rates']['rates']
        except Exception as e:
            logger.info('Could not establish redis exchange rate.')
            return None
        
    
    @staticmethod
    def get_rates_from_http():
        try:
            app_id = os.environ['EXCHANGE_RATE_APP_ID']
        except:
            raise Exception(MISSING_ENV_VAR_ERROR)
        
        url = 'https://openexchangerates.org/api/latest.json?app_id=%s&show_alternative=true' % app_id

        r = requests.get(url).json(parse_float=Decimal)

        return r['rates']

    @staticmethod
    @cache_me(time=60) # 1min
    def _all_rates():
        rates = USDCurrencyConverter.get_rates_from_redis()

        if not rates:
            rates = USDCurrencyConverter.get_rates_from_http()

        return rates
    
    @staticmethod
    def rate(currency_code):
        rates = USDCurrencyConverter._all_rates()
        rate = rates[currency_code]
        return rate

    @staticmethod
    @cache_me(time=600) # 10min
    def _historical_rates(year, month, day):
        """
        We can't cache this for longer because we check "historical" rate for today,
        which can change throughout the day.
        """
        try:
            app_id = os.environ['EXCHANGE_RATE_APP_ID']
        except:
            raise Exception(MISSING_ENV_VAR_ERROR)

        url = 'https://openexchangerates.org/api/historical/%d-%02d-%02d.json?app_id=%s&show_alternative=true' % (year, month, day, app_id)

        r = requests.get(url).json(parse_float=Decimal)

        return r['rates']

    @staticmethod
    def historical_rate(currency_code, date):
        historical_rates = USDCurrencyConverter._historical_rates(
            date.year,
            date.month,
            date.day,
        )

        rate = historical_rates[currency_code]

        return rate

