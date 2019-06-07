=====================
Exchange Integrations
=====================

The purpose of the gryphon exchange library is to wrap every exchange API in a standardized interface, such that any given exchange can easily be traded out with another when writing strategies. Without this layer, strategy designers would have to deal with a thousand implementation details between each exchange pair they wish to target, things like endpoint structure, rate limits, rounding behaviour, price/volume tick sizes, fee brackets. The exchange library abstracts all of this away from the strategy designer, so they can focus on developing trading behaviour.

.. _supported_exchange_list:

Supported Exchanges
-------------------

The following table shows the exchange trading pairs that are currently integrated into gryphon. All integrations pass the exchange validation unit tests, but some have processed much more volume than others, which gives extra confidence in their robustness.


+----------+--------+--------+--------------+
| Exchange | Pair   | Tested | Volume > $1m |
+----------+--------+--------+--------------+
| Gemini   | BTCUSD | Yes    | Yes          |
+          +--------+--------+--------------+
|          | BTCETH | Yes    | No           |
+          +--------+--------+--------------+
|          | ETHBTC | Yes    | No           |
+          +--------+--------+--------------+
|          | LTCUSD | Yes    | No           |
+          +--------+--------+--------------+
|          | ZECUSD | Yes    | No           |
+----------+--------+--------+--------------+
| Bitstamp | BTCUSD | Yes    | Yes          |
+          +--------+--------+--------------+
|          | BTCEUR | Yes    | No           |
+          +--------+--------+--------------+
|          | BCHEUR | Yes    | No           |
+          +--------+--------+--------------+
|          | BCHUSD | Yes    | No           |
+          +--------+--------+--------------+
|          | BCHBTC | Yes    | No           |
+          +--------+--------+--------------+
|          | ETHUSD | Yes    | No           |
+          +--------+--------+--------------+
|          | ETHEUR | Yes    | No           |
+          +--------+--------+--------------+
|          | ETHBTC | Yes    | No           |
+----------+--------+--------+--------------+
| Kraken   | BTCUSD | Yes    | Yes          |
+          +--------+--------+--------------+
|          | BTCCAD | Yes    | Yes          |
+          +--------+--------+--------------+
|          | BTCEUR | Yes    | Yes          |
+----------+--------+--------+--------------+
| Itbit    | BTCUSD | Yes    | Yes          |
+----------+--------+--------+--------------+
| Coinbase | BTCUSD | Yes    | Yes          |
+----------+--------+--------+--------------+
| OKCoin   | BTCUSD | No     | No           |
+----------+--------+--------+--------------+
| Bitfinex | BTCUSD | No     | No           |
+----------+--------+--------+--------------+


Exchange Trading Interface
--------------------------

The standardized interface that all exchange integrations conform to is called the Exchange Trading Interface. The superclass that defines it can be found at :py:mod:`gryphon.lib.exchange.exchange_api_wrapper`, although it lacks strong documentation at the moment. The core public methods of the interface are:

- :code:`get_orderbook()`
- :code:`get_open_orders()`
- :code:`get_balance()`
- :code:`place_order(mode, volume price=None, order_type=order_types.LIMIT_ORDER)`
- :code:`get_order_details(exchange_order_id)`
- :code:`cancel_order(exchange_order_id)`

There are additional methods that have implementations in the superclass using the core methods, but can be overridden in the child class if the exchange offers API endpoints for the functionality:

- :code:`cancel_all_open_orders()`
- :code:`get_multi_order_details([exchange_order_ids])`
- :code:`market_order(mode, volume)`
- :code:`limit_order(mode, volume, price)`
- :code:`get_price_quote()`

Some exchanges offer a ticker endpoint as well with summary details on the state of the market. This is not used in the strategy engine but can be useful to implement:

- :code:`get_ticker()`

If you want your integration to support order auditing, you also have to implement a function :code:`get_order_audit_data(self, skip_recent=0)`. This function returns a dictionary of recent orders on the current account to their filled volume as reported by the exchange, which is then compared against the records in the trading database. An example implementation can be seen in :py:mod:`gryphon.lib.exchange.bitstamp_btc_usd`.


Configuration
-------------

The exchange wrapper class has several properties that can be configured to reflect the state of your exchange accounts. These are parameters like limit/market order fee brackets, or rate limits, that can vary between users on an exchange, and which are important for your strategies to accurately take into account.

When you run a strategy in the strategy engine, you can tweak these properties in your strategy's :code:`.conf` file. To learn more about this, see :ref:`exchange_config`.

