.. _environment_reference:

==============================
Environment Variable Reference
==============================

Appendix of all the settings that can be listed in your :code:`.env` file to configure gryphon.

.. _environment_exchanges:

Exchange API Credentials
========================

Each exchange and trading pair needs it's own set of API credentials. Most exchanges
require an API key and secret, but some have extra entries they require. You can usually
find or generate these through the exchange's web UI.

Coinbase
--------

.. code-block:: bash

    COINBASE_BTC_USD_API_KEY
    COINBASE_BTC_USD_API_SECRET
    COINBASE_BTC_USD_API_PASSPHRASE

Kraken
------

.. code-block:: bash

    KRAKEN_BTC_USD_API_KEY
    KRAKEN_BTC_USD_API_SECRET

    KRAKEN_BTC_EUR_API_KEY
    KRAKEN_BTC_EUR_API_SECRET

    KRAKEN_BTC_CAD_API_KEY
    KRAKEN_BTC_CAD_API_SECRET


Gemini
------

.. code-block:: bash

    GEMINI_BTC_USD_API_KEY
    GEMINI_BTC_USD_API_SECRET

    GEMINI_BTC_ETH_API_KEY
    GEMINI_BTC_ETH_API_SECRET

    GEMINI_ETH_USD_API_KEY
    GEMINI_ETH_USD_API_SECRET

Bitstamp
--------

.. code-block:: bash

    BITSTAMP_BTC_USD_API_SECRET
    BITSTAMP_BTC_USD_API_KEY
    BITSTAMP_BTC_USD_CLIENT_ID

    BITSTAMP_BTC_EUR_API_SECRET
    BITSTAMP_BTC_EUR_API_KEY
    BITSTAMP_BTC_EUR_CLIENT_ID

    BITSTAMP_ETH_USD_API_KEY
    BITSTAMP_ETH_USD_API_SECRET
    BITSTAMP_ETH_USD_CLIENT_ID

    BITSTAMP_ETH_EUR_API_KEY
    BITSTAMP_ETH_EUR_API_SECRET
    BITSTAMP_ETH_EUR_CLIENT_ID

    BITSTAMP_ETH_BTC_API_KEY
    BITSTAMP_ETH_BTC_API_SECRET
    BITSTAMP_ETH_BTC_CLIENT_ID

    BITSTAMP_BCH_BTC_API_KEY
    BITSTAMP_BCH_BTC_API_SECRET
    BITSTAMP_BCH_BTC_CLIENT_ID

    BITSTAMP_BCH_EUR_API_KEY
    BITSTAMP_BCH_EUR_API_SECRET
    BITSTAMP_BCH_EUR_CLIENT_ID

Itbit
-----

.. code-block:: bash

    ITBIT_USER_ID
    ITBIT_API_KEY
    ITBIT_API_SECRET
    ITBIT_WALLET_ID

.. _environment_general:

General settings
================

.. code-block:: bash

    # The trading database mysql url.
    TRADING_DB_CRED

    # Your Open Exchange Rates token.
    EXCHANGE_RATE_APP_ID

    SENTRY_URL
    REDIS_URL

