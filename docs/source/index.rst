.. gryphon-framework documentation master file, created by
   sphinx-quickstart on Tue Dec 11 16:16:51 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Gryphon Trading Framework 0.12 Documentation
=============================================

Gryphon is an open source software platform for building and running algorithmic trading strategies in cryptocurrency markets. It has traded billions in volume to date.

This documentation should tell you everything you need to know about Gryphon.

Starting Out
============

Gryphon is both a software library that can be integrated into other projects, and an application suite for running trading strategies and operating a trading business. How you use Gryphon depends on your goals.

This documentation is primarily for users wanting to use gryphon to run their own trading business, but the API documentation in particular will be relevant to all users.

We recommend starting out by following along in the :ref:`installation` document, and then proceeding on to :ref:`use_for_trading`.

Demo Strategy
=============

Here is a simple, one-way arbitrage strategy built on gryphon.

.. code-block:: python

    from gryphon.execution.strategies.base import Strategy
    from gryphon.lib import arbitrage as arb


    class SuperSimpleArb(Strategy):
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
                self.harness.gemini_btc_usd.market_order(executable_volume, 'BID')
                self.harness.coinbase_btc_usd.market_order(executable_volume, 'ASK')

A near-cousin to this strategy ships built-in to the framework at :py:mod:`gryphon.execution.strategies.builtin.simple_arb` and can be run on an appropriate installation with the command:

.. code-block:: bash

    gryphon-exec strategy simple_arb --builtin --execute

Getting Help
============

.. _github: https://github.com/TinkerWork/gryphon/issues
.. _`tag 'gryphonframework'`: https://stackoverflow.com/questions/tagged/gryphonframework
.. _slack: https://gryphonframework.slack.com
.. _`this link`: https://join.slack.com/t/gryphonframework/shared_invite/enQtNjYxNjEzNTUzNzY0LTA5MWExYWM4ZTk1YTg1MzVjMTkwMDU4ZTA5ZWVmYWJmZjk1MTQ3MjdkNmZiNDQ1ODRjM2U2MTBhMjc5YWIzYWM

There are a few ways to get help with Gryphon:

- Join the gryphon slack_ to ask a question to the developers (use `this link`_ to get an invite if you don't already have one)
- Ask a question on stackoverflow with the `tag 'gryphonframework'`_
- Report bugs on github_
- Search these docs using the searchbar in the top left

Documentation
=============

.. toctree::
   :caption: Starting Out

   installation
   usage

.. toctree::
   :caption: In Depth

   writing_strategies
   exchange_integrations
   advanced_features
   ledger
   dashboards
   data_service
   business
   configuration

.. toctree::
   :caption: Reference

   contributing
   style
   environment
   reading_list

Appendices
==========

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
