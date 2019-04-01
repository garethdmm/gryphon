from gryphon.execution.lib.exchange_color import exchange_color
from gryphon.lib.exchange.exchange_factory import *
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib import session

logger = get_logger(__name__)


def balance_requests(exchanges):
    balance_requests = []
    for exchange in exchanges:
        balance_requests.append(exchange.get_balance_req())
    return balance_requests


def balance_responses(exchanges, balance_requests):
    """
    This function uses environment variables to set
    a minimum balances for an exchange. 
    Format:{{exchange.name}}_MINIMUM_USD
    Examples: BITSTAMP_MINIMUM_USD, CAVIRTEX_MINIMUM_BTC
    """
    balances = {}
    balances['system'] = Balance()

    for exchange in exchanges:
        req = balance_requests.pop(0)
        balances[exchange.name] = exchange.get_balance_resp(req)
        balances['system']['USD'] += balances[exchange.name].fiat().to('USD')
        balances['system']['BTC'] += balances[exchange.name]['BTC']
    return balances


def get_db_balances(exchanges):
    db = session.get_a_trading_db_mysql_session()

    db_balances = {}
    db_balances['system'] = Balance()
    try:
        for exchange in exchanges:
            exchange_data = exchange.exchange_account_db_object(db)
            db_balances[exchange.name] = exchange_data.balance
            db_balances['system']['USD'] += db_balances[exchange.name].fiat().to('USD')
            db_balances['system']['BTC'] += db_balances[exchange.name]['BTC']
    finally:
        db.close()
    return db_balances


def format_balances(exchange_balances, db_balances):
    output_string = u"\n{0:15} : {1:15} | {2:15} || {3:15} | {4:15}\n".format("Balances", "FIAT", "BTC", "dbFIAT", "dbBTC")
    for name, balance in sorted(exchange_balances.iteritems()):
        db_balance = db_balances[name]
        chunk = u"{0:15} : {1:15} | {2:15.8f} || {3:15} | {4:15.8f}\n".format(
            name,
            balance.fiat(),
            balance['BTC'].amount,
            db_balance.fiat(),
            db_balance['BTC'].amount
            )
        chunk = exchange_color(chunk, name)
        output_string += chunk
    
    return output_string

    
def balance(exchange_name):
    if exchange_name:
        exchange = make_exchange_from_key(exchange_name)
        exchanges = [exchange]
    else:
        exchanges = all_exchanges()
    brs = balance_requests(exchanges)
    balances = balance_responses(exchanges, brs)

    db_balances = get_db_balances(exchanges)

    print(format_balances(balances, db_balances))
