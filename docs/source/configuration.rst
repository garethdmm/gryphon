.. _configuration:

=============
Configuration
=============

Basics Concepts
---------------

There are lots of settings inside gryphon that can be tweaked between runs. Some of these are engine set-up parameters, like whether or not to log errors to a 3rd party service, some are these are specific numeric parameters to strategies, like a lookback window for a bollinger band signal, and some are obscure. To tweak these settings between runs of the strategy engine, Gryphon uses a format called :code:`.conf` files.

Conf files are simple lists of key-value pairs, sometimes grouped under a section heading. Here’s an example:

   .. code-block:: bash

    [platform]
    audit: no
    emerald: no

    [strategy]
    tick_sleep: 4
    base_volume: BTC 0.002
    spread: 0.002

    [bitstamp_btc_usd]
    market_order_fee: 2.00
    emerald: no


Gryphon will try to parse the values of these parameters into python types intelligently, and if no appropriate type can be found, the value is loaded as a string. Here are the supported value formats in order of parsing order:

+-------------+------------------------------------+--------------------+
| Python type | String Format                      | Example            |
+=============+====================================+====================+
| Boolean     | "yes" or "no"                      | yes                |
+-------------+------------------------------------+--------------------+
| Money       | "[currency code] [numeric amount]" | BTC 2.35           |
+-------------+------------------------------------+--------------------+
| Decimal     | "[numeric amount]"                 | 0.22147            |
+-------------+------------------------------------+--------------------+
| String      | Anything else                      | bitstamp_btc_usd   |
+-------------+------------------------------------+--------------------+

Gryphon can also handle comma separated list values, but this must be done explicitly by the strategy writer.

Note that this type of configuration has nothing to do with secret credentials, which are handled in :code:`.env` files.

A given configuration is associated with a strategy, and is loaded by the engine at runtime. The engine by default loads the configuration from a file named after the strategy with the .conf suffix. You can provide a path to a different location by passing the parameter :code:`-c/--config_file` to the engine.

Three components of Gryphon are configurable: the target strategy, the exchange integrations, and the engine itself. 

.. _strategy_config:

Strategy Configuration
----------------------

You will very likely want to write strategies with parameters that can be changed between executions, like a spread width, or a lookback time, etc. These parameters can be placed under a section :code:`[strategy]` in the .conf file, and they will be passed to your strategy class on start-up.

To write your strategy to accept a configuration parameter, here are the steps:

#. Define the property with a default in the constructor, or with a :code:`None` value to require it from the user.
#. Implement the function :code:`configure(self, strat_config)`, being sure to call the superclass implementation as the first line of this function.
#. Inside :code:`configure`, call this :code:`self.init_configurable([name], strat_config)` for each property you want to be configurable.

Here is an exceprt of the SimpleMarketMaking builtin strategy that shows how this all fits together.


   .. code-block:: python

    class SimpleMarketMaking(Strategy):
        def __init__(self, db, harness, strategy_configuration):
            super(SimpleMarketMaking, self).__init__(db, harness)

            # Configurable properties with defaults.
            self.spread = Decimal('0.01')
            self.base_volume = Money('0.005', 'BTC')
            self.exchange = None

            self.configure(strategy_configuration)

        def configure(self, strategy_configuration):
            super(SimpleMarketMaking, self).configure(strategy_configuration)

            self.init_configurable('spread', strategy_configuration)
            self.init_configurable('base_volume', strategy_configuration)
            self.init_configurable('exchange', strategy_configuration)


Feel free to do any other custom configuration work in your configure() function.

.. _engine_config:

Engine Configuration
--------------------

The engine can be configured in a section of the config file headed "platform". Here are the current supported engine config settings with example (but not default) settings:

   .. code-block:: bash

    [platform]
    audit: no
    audit_tick: 100
    audit_types: ledger, volume_balance
    sentry: no
    emerald: no

Note that all of these can be set or overridden at the command line as well by prefacing the parameter name with two dashes.

Here's a short explanation of each parameter:

- :code:`audit` - Whether to turn on auditing.
- :code:`audit_tick` - Audit every :code:`n` ticks.
- :code:`audit_types` - Comma separated list of audit types to perform.
- :code:`emerald` - Whether to use fast market data from GDS or perform market data IO operations in the same thread as the trading code (the default).
- :code:`sentry` - Whether to send log messages and errors to the 3rd party logging service sentry, requires it's own setup.

.. _exchange_config:

Exchange Pair Configuration
---------------------------

There are many parameters to exchange accounts that can change over time or be different between users. The most obvious is fee levels, which are usually a function of a user's recent volume on that exchange, but there are other parameters like minimum order sizes that are important to set accurately too.

The strategy engine loads configuration information for each exchange pair from a section in the config file labelled with the pair's name, like :code:`bitstamp_btc_usd`. You can add a section for each pair that you plan to trade with using the strategy.

Here’s a fully filled out section for coinbase btcusd:

   .. code-block:: bash

    [coinbase_btc_usd]
    market_order_fee: 0.003
    limit_order_fee: 0.001
    max_tick_speed: 2
    fiat_balance_tolerance: USD 0.01
    volume_balance_tolerance: BTC 0.00000001
    use_cached_orderbook: no

Each pair has defaults for each of these parameters, but you should override them as necessary. :code:`volume/fiat_balance_tolerance` are only relevant if you are using auditing in the engine, and :code:`use_cached_orderbook` is only relevant if you are running GDS in parallel to your strategies.

