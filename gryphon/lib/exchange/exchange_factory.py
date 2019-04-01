# -*- coding: utf-8 -*-

from gryphon.lib.exchange import exceptions


ALL_EXCHANGE_KEYS = [
    'bitstamp_btc_usd',
    'bitfinex_btc_usd',
    'kraken_btc_eur',
    'kraken_btc_usd',
    'kraken_btc_cad',
    'itbit_btc_usd',
    'okcoin_btc_usd',
    'coinbase_btc_usd',
    'quadriga_btc_cad',
    'gemini_btc_usd',
]

HISTORICAL_EXCHANGE_KEYS = [
    'vaultofsatoshi_btc_cad',
    'bitme_btc_usd',
    'buttercoin_btc_usd',
    'cavirtex_btc_cad',
    'coinsetter_btc_usd',
]

BANK_ACCOUNT_KEYS = ['BMO_USD', 'BMO_CAD', 'BMO_CAD_OPS', 'BOA_MAIN', 'BOA_INCOME']


def all_exchanges():
    return [make_exchange_from_key(key) for key in ALL_EXCHANGE_KEYS]


def all_exchange_datas(db):
    return make_exchange_datas_from_keys(ALL_EXCHANGE_KEYS, db)

def all_bank_accounts(db):
    return make_exchange_datas_from_keys(BANK_ACCOUNT_KEYS, db)

def historical_exchanges():
    return [make_exchange_from_key(key) for key in HISTORICAL_EXCHANGE_KEYS]


def historical_exchange_datas(db):
    return make_exchange_datas_from_keys(HISTORICAL_EXCHANGE_KEYS, db)


def all_current_and_historical_exchanges():
    current_exchanges = all_exchanges()
    current_exchanges.extend(historical_exchanges())

    return current_exchanges


def canonical_key(key):
    key = key.upper()
    if key == 'VAULT':
        key = 'VAULTOFSATOSHI'
    if key == 'BUTTER':
        key = 'BUTTERCOIN'

    return key


def map_pair_name_to_exchange_name(pair_name):
    """
    We're preparing to add the notion that exchanges can have multiple trading pairs
    into our system. Each exchange is going to have a single ExchangeData db object but
    have one wrapper for each pair. Order.exchange_name is going to refer to the pair,
    but most accounting functions take place on the ExchangeData object. Thus, we need
    a mapping of ExchangeWrapper -> ExchangeData. This function will serve that purpose
    for now.
    """

    if pair_name == 'GEMINI_ETH_USD':
        return 'GEMINI_BTC_USD'
    else:
        return pair_name


def make_exchange_from_key(key):
    key = canonical_key(key)

    api_wrapper_class = get_api_wrapper_class_by_name(key)

    return api_wrapper_class()


def make_exchange_data_from_key(key, db):
    keys = [key]
    exchange_datas = make_exchange_datas_from_keys(keys, db)

    assert len(exchange_datas) == 1

    return exchange_datas[0]


def initialized_ledgers(db):
    """
    Give us the names of the exchanges that have initialized ledgers in our trading
    database.
    """
    from gryphon.lib.models.exchange import Exchange as ExchangeData

    exchange_account_names = db.query(ExchangeData.name).all()
    exchange_account_names = [e[0] for e in exchange_account_names]

    return exchange_account_names


def get_all_initialized_exchange_wrappers(db):
    from gryphon.lib.models.exchange import Exchange as ExchangeData

    exchange_accounts = db.query(ExchangeData).all()

    exchange_wrappers = [
        make_exchange_from_key(e.name) for e in exchange_accounts
        if e.name.lower() in ALL_EXCHANGE_KEYS
    ]

    return exchange_wrappers


def make_exchange_datas_from_keys(pair_names, db):
    from gryphon.lib.models.exchange import Exchange as ExchangeData

    canonical_pair_names = [canonical_key(k) for k in pair_names]
    exchange_names = [map_pair_name_to_exchange_name(p) for p in canonical_pair_names]

    exchange_datas = db.query(ExchangeData)\
        .filter(ExchangeData.name.in_(exchange_names))\
        .all()

    assert len(exchange_datas) == len(pair_names)

    return [exchange_datas[0]]


def get_api_wrapper_class_by_name(exchange_name):
    exchange_name = canonical_key(exchange_name)

    if exchange_name == 'BITSTAMP_BTC_USD':
        from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
        return BitstampBTCUSDExchange
    elif exchange_name == 'BITSTAMP_ETH_EUR':
        from gryphon.lib.exchange.bitstamp_eth_eur import BitstampETHEURExchange
        return BitstampETHEURExchange
    elif exchange_name == 'BITSTAMP_ETH_USD':
        from gryphon.lib.exchange.bitstamp_eth_usd import BitstampETHUSDExchange
        return BitstampETHUSDExchange
    elif exchange_name == 'BITSTAMP_ETH_BTC':
        from gryphon.lib.exchange.bitstamp_eth_btc import BitstampETHBTCExchange
        return BitstampETHBTCExchange
    elif exchange_name == 'BITSTAMP_ETH_EUR':
        from gryphon.lib.exchange.bitstamp_eth_eur import BitstampETHEURExchange
        return BitstampETHEURExchange
    elif exchange_name == 'BITSTAMP_BTC_EUR':
        from gryphon.lib.exchange.bitstamp_btc_eur import BitstampBTCEURExchange
        return BitstampBTCEURExchange
    elif exchange_name == 'BITSTAMP_BCH_BTC':
        from gryphon.lib.exchange.bitstamp_bch_btc import BitstampBCHBTCExchange
        return BitstampBCHBTCExchange
    elif exchange_name == 'BITSTAMP_BCH_USD':
        from gryphon.lib.exchange.bitstamp_bch_usd import BitstampBCHUSDExchange
        return BitstampBCHUSDExchange
    elif exchange_name == 'BITSTAMP_BCH_EUR':
        from gryphon.lib.exchange.bitstamp_bch_eur import BitstampBCHEURExchange
        return BitstampBCHEURExchange
    elif exchange_name == 'KRAKEN_BTC_EUR':
        from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
        return KrakenBTCEURExchange
    elif exchange_name == 'KRAKEN_BTC_USD':
        from gryphon.lib.exchange.kraken_btc_usd import KrakenBTCUSDExchange
        return KrakenBTCUSDExchange
    elif exchange_name == 'KRAKEN_BTC_CAD':
        from gryphon.lib.exchange.kraken_btc_cad import KrakenBTCCADExchange
        return KrakenBTCCADExchange
    elif exchange_name == 'BITFINEX_BTC_USD':
        from gryphon.lib.exchange.bitfinex_btc_usd import BitfinexBTCUSDExchange
        return BitfinexBTCUSDExchange
    elif exchange_name == 'ITBIT_BTC_USD':
        from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
        return ItbitBTCUSDExchange
    elif exchange_name == 'OKCOIN_BTC_USD':
        from gryphon.lib.exchange.okcoin_btc_usd import OKCoinBTCUSDExchange
        return OKCoinBTCUSDExchange
    elif exchange_name == 'QUADRIGA_BTC_CAD':
        from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
        return QuadrigaBTCCADExchange
    elif exchange_name == 'COINBASE_BTC_USD':
        from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
        return CoinbaseBTCUSDExchange
    elif exchange_name == 'GEMINI_BTC_USD':
        from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
        return GeminiBTCUSDExchange
    elif exchange_name == 'GEMINI_ETH_USD':
        from gryphon.lib.exchange.gemini_eth_usd import GeminiETHUSDExchange
        return GeminiETHUSDExchange
    elif exchange_name == 'GEMINI_ETH_BTC':
        from gryphon.lib.exchange.gemini_eth_btc import GeminiETHBTCExchange
        return GeminiETHBTCExchange
    elif exchange_name == 'POLONIEX_ETH_BTC':
        from gryphon.lib.exchange.poloniex_eth_btc import PoloniexETHBTCExchange
        return PoloniexETHBTCExchange
    else:
        raise exceptions.ExchangeNotIntegratedError(exchange_name)

