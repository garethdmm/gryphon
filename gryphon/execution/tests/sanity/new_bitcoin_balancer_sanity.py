import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Console")
from utils.balancer import proportions, account_value_limits, bitcoin_rebalance
from gryphon.lib.money import Money

def sanity_bitcoin_rebalance(db, exchange_data, other_exchange_data):
    logger.info('SANITY TEST FOR BITCOIN REBALANCER')
    logger.info('!!!!!!!!!!!!!!!!! USE ONLY WITH TEST / STAGIN DB. THIS WILL LOCK THE DB !!!!!!!!!!!!!!!!!!!')
    
    # Test 1 - exchange_data will not send bitcoin
    exchange_data.balance['BTC'] = Money(0, 'BTC')
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULT %s will be the exchange most in need. Wont send to self.\n\n' % exchange_data.name)
    
    # Test 2 - exchange_data will send to other exchange_data
    exchange_data.balance['BTC'] = Money(50000, 'BTC')
    other_exchange_data.balance['BTC'] = Money(0, 'BTC')
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULT %s will send to %s or another exchange with 0 BTC.\n\n' % (exchange_data.name, other_exchange_data.name))
    
    # Test 3 - not send due to account limit
    exchange_data.balance['BTC'] = Money(50000, 'BTC')
    other_exchange_data.balance['BTC'] = Money(500, 'BTC')
    other_exchange_data.balance['USD'] += account_value_limits[other_exchange_data.name] 
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULT %s will not send to %s because it is above its limit. Should send to another exchange. \n\n' % (exchange_data.name, other_exchange_data.name))
    
    #Test 4 - exchanges are only 9btc apart
    exchange_data.balance['BTC'] = Money(70, 'BTC')
    exchange_data.balance['USD'] = account_value_limits[exchange_data.name]/2
    other_exchange_data.balance['BTC'] = Money(61, 'BTC')
    other_exchange_data.balance['USD'] = account_value_limits[other_exchange_data.name]/2
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULTS: %s will not send to %s becuase the exchanges are close together. This test aint perfect.\n\n' % (exchange_data.name, other_exchange_data.name) )
    
    #Test 5 - exchanges are only 15btc apart
    exchange_data.balance['BTC'] = Money(75, 'BTC')
    exchange_data.balance['USD'] = account_value_limits[exchange_data.name]/2
    other_exchange_data.balance['BTC'] = Money(55, 'BTC')
    other_exchange_data.balance['USD'] = account_value_limits[other_exchange_data.name]/2
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULTS: %s will  send to %s becuase the exchanges are close together but far enough apart. This test aint perfect.\n\n' % (exchange_data.name, other_exchange_data.name) )
    
    #Test 6 - exchanges has more than its target in full balance but less than its target in its balance, it should not send
    exchange_data.balance['BTC'] = Money(10, 'BTC')
    other_exchange_data.balance['BTC'] = Money(110, 'BTC')
    other_exchange_data.record_withdrawal(exchange_data, Money(100, 'BTC'), None, None, None)
    bitcoin_rebalance(db, exchange_data, False)
    logger.info('EXPECTED TEST RESULT: %s will not send to %s becuase it doesnt have enough in its balance, even though it has lots in its full_balance'  % (exchange_data.name, other_exchange_data.name))
    
    
    
    
