.. _writing_strategies:

==================
Writing Strategies
==================

.. _strategy_architecture:

Basic Architecture
==================

In gryphon, strategies are executed with the command:

   .. code-block:: bash

      gryphon-exec strategy [strategy_filepath]


This launches the Strategy Engine, and loads the given strategy file into it. Strategies are simple python files and classes that conform to a loose specification allowing the engine to understand and execute them. In return, the engine provides functionality like exchange connections, fault tolerance, state tracking, ledger accuracy guarantees, and tons of other features that would need to be re-implmented by every user, and for every strategy.

When strategies are launched they are given a reference back to the engine instance, at :code:`self.harness` (it's safe to ignore the phrase 'harness' here and just think of it as the same thing as the engine). Inside the strategy this reference gives access to the most frequently used features of the engine. For example, querying bitstamp for the latest orderbook is done with:

   .. code-block:: python

      self.harness.bitstamp_btc_usd.get_orderbook()

As you get more familiar with Gryphon it's important to understand the internals of the engine and the breadth of functionality it offers. We dig into that in the section strategy_engine_. For now we'll show you what the basic structure of strategies is and give guidance on how to build more and more complex behaviour into them.


The Structure of a Strategy
===========================

Minimal Spec
------------

Strategies are python classes which inherit from gryphon.execution.strategies.base.Strategy and define a function :code:`tick(current_orders)`. This class should exist in a file with a filename that matches the classname case-insensitively. The following is the minimum valid strategy:

   .. code-block:: python

    from gryphon.execution.strategies.base import Strategy

    class MinimalStrategy(Strategy):
        def tick(self, current_orders):
            pass

Strategy execution proceeds by repeated calls to :code:`tick()`.

Writing your tick function
--------------------------

The :code:`tick()` function should be a simple structure: 

#. Look at the outcome of the last tick and the current state of the markets
#. Make trading decisions
#. Place/cancel/modify orders

That is to say, a “tick” a single observe-decide-act structure, and your strategies should be built in such a way that the same decision making ruleset, executed repeatedly over time, creates a coherent trading behaviour.

For example, in the ‘super_simple_market_making’ strategy, the steps are:

#. Get the current orderbook for our target exchange
#. Calculate a new bid/ask price around the midpoint and associated order volumes
#. Cancel any orders left over from our last tick
#. Place our new orders

For a very simple set of instructions, this observe-decide-act flow can create very coherent trading patterns.


.. _exchange_inteface:

Interacting with Exchanges
--------------------------

The engine provides the strategies with connections to all the exchanges which are integrated in gryphon which are pre-set up, have redundancy layers around them, and auto-sync with the trading database. They are accessed through the harness, such as :code:`self.harness.coinbase_btc_usd`. You should always always interact with exchanges through the engine connections, never set up your own directly through the gryphon.lib.exchange library.

While all the public market data functions of exchanges are available immediately, in order to use their authenticated endpoints like getting balance information, placing orders, you need to have set up the credentials for those exchanges in your :code:`.env`, and started a ledger for that pair, as seen in :ref:`exchange_ledger_basics`.

The basic interface for an exchange trading pair is uniform across all integrated exchanges:

- :code:`get_orderbook(self)`
- :code:`get_open_orders()`
- :code:`get_order_details(self, exchange_order_id)`
- :code:`cancel_order(self, exchange_order_id)`
- :code:`get_balance(self)`
- :code:`place_order(self, mode, volume price=None, order_type=order_types.LIMIT_ORDER)`

Gryphon currently supports 20 trading pairs over 7 exchanges. You can see the list at :ref:`supported_exchange_list`.

Knowing your strategy's state
-----------------------------

Under the hood, as your strategies place orders and make trades, the engine is keeping track of every action they take in the trading database. This means that the strategy's entire trading history is available to the user with no extra effort, which is usually sufficient to derive any state information the strategy needs to make it's next decision.

Two of the most commonly used state properties are available immediately inside the :code:`tick()` function. The first is the strategy's position, which is available as the property :code:`self.position`. The second is the list of any presently open orders associated with the strategy. These are passed as the first argument to the tick function, as :code:`tick(current_orders)`.

You can also query the trading database directly. There is always an active databse connection available through the engine as :code:`self.harness.db`.

