.. _use_for_trading:

=========================
Using Gryphon for Trading
=========================

Basic Concepts
==============

.. _executable:

Strat-runner executable
-----------------------

Gryphon installs four command line tools in your PATH. The most important by far is the
strategy-runner: :code:`gryphon-execute`. It's primary function is to load and execute
your strategies on the markets, which is done as follows:

.. code-block:: bash

    gryphon-execute strategy [strategy_file] [--builtin] [--execute]

If you run a strategy without the :code:`--execute` flag, the strategy file executes in
full, but no order-placement calls will be made to exchanges. This is very useful
for testing and debugging strategies.


.. _dotenv_files:

Handling credentials with .env files
------------------------------------

Gryphon interacts with exchanges and a few other third party services through their
APIs, which requires gryphon to read your credentials for those services. To prevent
these credentials from accidentally being e.g. committed to your source control or
otherwise trasmitted, gryphon reads these credentials from a simple file on your
machine named :code:`.env`, pronounced 'dotenv' or sometimes just 'env'.

These files are a simple list of key=value pairs. For example, the entries in your
:code:`.env` file for coinbase's api look like this:

.. code-block:: bash

    COINBASE_BTC_USD_API_KEY=[YOUR KEY]
    COINBASE_BTC_USD_API_SECRET=[YOUR SECRET]
    COINBASE_BTC_USD_API_PASSPHRASE=[YOUR PASSPHRASE]

:code:`gryphon-execute` and the other tools always read from the dotenv file in the
current working directory. This means we recommend that you have only a single such file
on your machine in a directory designated for running gryphon.

.. _directory_structure:

Recommended directory structure
-------------------------------

If you plan to use gryphon for anything more than cursory trading, it's recommended that
you create a designated directory to hold your dotenv, strategy files, and
other configuration files. This can also be the root of your source control repository.
A very simple gryphon-root looks like this:

.. code-block:: bash

    my-gryphon-root/
      strategies/
        mystrat.py
        __init__.py
      .env

This may seem like overkill right now, but once you have many of your own strategies,
their associated configuration files, and custom dotenv and config files for your
dashboards and maybe GDS, you'll be happy you set up a sane directory structure early
on.

.. _exchange_ledger_basics:

Exchange Ledgers
----------------

Gryphon tracks every order, trade, deposit, and withdrawal your strategies make in it's
trading database. The set of these records that are associated with a given
exchange are called it's 'Exchange Ledger'. Before we can use an exchange with gryphon
it's necessary to initialize a ledger for it, which can be done easily with a utility
function in :code:`gryphon-execute`.

First, add the API credentials for that exchange to our dotenv. You can
find what credentials your chosen exchange needs in the :ref:`dotenv_reference`.

Then run the :code:`initialize_exchange_ledgers` script.

.. code-block:: bash

    gryphon-execute script initialize_exchange_ledgers\
        --exchanges [comma-separated list of exchanges]\
        --execute

This script is one of the utility functions that is also available through
:code:`gryphon-execute`. It queries your balance information from the exchange API
and creates an entry in the trading database to represent this exchange account.

Whenever you want to add a new exchange to trade on, run this script first to start a
ledger for it.

.. _running_strategies:

Running Strategies
==================

.. _run_builtin_strat:

Run a built-in strategy
-----------------------

Gryphon ships with a few simple built-in strategies. These aren't designed for serious
trading but can be useful for testing and learning the framework.

One such strategy is called 'Simple Market Making'. It can be run as follows:

.. code-block:: bash

    gryphon-execute strategy simple_market_making --builtin

This will run the strategy in no-execute mode. If you want it to place real orders, add
the :code:`--execute` flag to the same command. If you are running from a completely
clean installation, you'll find that throws an error like this:

.. code-block:: bash

    KeyError: u'BITSTAMP_BTC_USD_API_KEY'

That is because Simple Market Making runs on bitstamp, and you haven't added your API
keys for bitstamp to your dotenv file yet. To do so, add these keys to your dotenv:

.. code-block:: bash

    BITSTAMP_BTC_USD_API_KEY=[YOUR KEY]
    BITSTAMP_BTC_USD_API_SECRET=[YOUR SECRET]
    BITSTAMP_BTC_USD_API_PASSPHRASE=[YOUR PASSPHRASE]

Now, try running the strategy again. You should start to see some simple logging
that shows the platform is ticking.

.. _run_custom_strat:

Write and run a custom strategy
--------------------------------

Gryphon has a lot of building-block libraries that make common tasks quite simple. For
example, we can use the gryphon arbitrage library to write a simple arbitrage strategy
in only three major function calls.

Starting from your gryphon root again, create a file: :code:`strategies/arb.py`, and
copy this text into it.

.. code-block:: python

    from gryphon.execution.strategies.base import Strategy
    from gryphon.lib import arbitrage as arb 
    from gryphon.lib.exchange.consts import Consts

    class Arb(Strategy):
        def tick(self, open_orders):
            cross = arb.detect_directional_cross(
                self.harness.gemini_btc_usd.get_orderbook(),
                self.harness.coinbase_btc_usd.get_orderbook(),
            )   

            executable_volume = arb.get_executable_volume(
                cross,
                self.harness.coinbase_btc_usd.get_balance(),
                self.harness.gemini_btc_usd.get_balance(),
            )   

            if cross and executable_volume:
                self.harness.gemini_btc_usd.market_order(executable_volume, Consts.BID)
                self.harness.coinbase_btc_usd.market_order(executable_volume, Consts.ASK)

If you don't use Gemini or Coinbase, it's fine to switch either of those out with
another btc-usd pair you use that is supported by gryphon, just so long as you
remember to add their credentials to the dotenv and start a ledger.

Now, run your custom strategy in no-execute mode with:

.. code-block:: bash

    gryphon-execute strategy strategies/arb.py

Again, you should see some boilerplate logging that shows the platform is ticking, but
not as much as when we ran the built-in strategy. That's because we haven't added any
log messages to the strategy that tell the viewer what is going on, but we'll get to
that.

Congratulations, you are trading with Gryphon!

