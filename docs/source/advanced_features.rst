.. _advanced_features:

========================
Advanced Engine Features
========================


.. _auditing:

Auditing
========

Account auditing is one of the most powerful features of gryphon when used properly, and can give you an extreme level of confidence that your strategies are operating as should.

The purpose of auditing is to check that the state of your exchange accounts in the trading database matches the state reported by the exchange's API. This is good for a couple reasons:

#. Catches strategy bugs early
#. Guarantees that your strategies are operating on accurate position, p&l, and other data
#. Guarantees that your financial reporting to authorities will be accurate
#. When used in combination with alerting, can get a human in front of a problem instantly, vs. potentially days later.

In general, you will find that a lot can go slightly wrong in high volume trading, and slight issues can compound quickly, so checking that everything lines up every few minutes (or faster) will save a lot of time and money in the long run.

If you plan to do frequent trading on your accounts that is not done with Gryphon, it may be difficult to use auditing, as you'll have to record every trade performed on the accounts in the trading database as well to keep the ledger and balances lined up. On some exchanges it's easy to get around this by using sub-accounts or other mechanisms.

Audits in the Strategy Engine
-----------------------------

Auditing is built into the engine but is disabled by default. You can turn it on by adding the line :code:`audit: yes` to the :code:`platform` section of your :code:`.conf`, or adding the command line flag :code:`--audit` when you run a strategy.

Two other parameters configure the type and frequency of audits. A full section is shown here:

   .. code-block:: bash

      [platform]
      audit: yes
      audit_tick: 100
      audit_types: ledger, order

The engine performs an audit at the end of every :code:`audit_tick`'th tick. There are three different checks performed in an audit, and you can configure which ones the engine will run with the parameter :code:`audit_types`. You can see these constants defined in :py:mod:`gryphon.execution.lib.auditing`.

The engine keeps track of activity on it's exchange connections, and will perform an audit on every exchange that has placed an order or made a transaction since the last audit. You can also specify in your strategies certain exchanges to always audit, by adding their pair name to the :code:`target_exchanges` property on the strategy.

Manual Audits
-------------

You can also trigger an audit manually by running:

   .. code-block:: bash

      gryphon-exec audit [exchange_pair_name]

This is very useful for diagnosing ledger issues.

Audit Types
-----------


-------------
Balance Audit
-------------

The balance audit check queries the exchange for the current account balance and compares it to what is recorded for that exchange pair in trading database. If the difference is below the tolerance for that pair, the engine raises an exception.

Tolerance defaults are defined for both the price and volume currency of a pair in the exchange integration, as :code:`fiat_balance_tolerance` (the term 'fiat' here is vestigial from the early days when Gryphon only used fiat-crypto pairs) and :code:`volume_balance_tolerance` . The given defaults tend to be restrictive, so these can be overridden in the :code:`.conf` file as seen in :ref:`exchange_config`.

Drift
.....

When a balance audit finds a balance mismatch that is smaller than the tolerances you've defined, this is called 'Drift'. Small amounts of drift are normal on some exchange pairs, in the range of cents-per-$100k of volume, and is unlikely to matter to your strategies p&l (exchange fees are 100-1000x larger). Drift is most commonly caused when the rounding behaviour in Gryphon does not perfectly match that used inside the exchange itself, this might sound like a simple issue to solve, but when we're using 8 or more decimal places of precision, it can be quite difficult to nail.

Nevertheless, when drift occurs, the engine makes a record of it in the :code:`Transaction` table. This allows the exchange ledger to continue to line up with what the exchange API reports, and also allows us to track the amount of drift we encounter over time to make sure it stays at trivial levels.

------------
Ledger Audit
------------

In the trading database, there are two ways to know what the balance of an exchange account are. The first is in the Exchange table, where each ledger has a single entry, on which there is a record of it's current balance. This record is updated every time a trade or transaction is made. The second is the ledger itself: the set of all trades, transactions, and drift that is associated with that account. If sum up all the entries in the ledger, you can find an implied balance for the account. 

The Ledger Audit checks that the ledger-implied balance matches the balance in the Exchange table. If they do not match, something has gone wrong.

It's easy to confuse the Ledger audit with the Balance audit. Here's the difference: the Balance audit checks the Exchange table against the response from exchange's API, so it's an internal-external check. The Ledger audit is a check for internal consistency in the trading database.

You can enable ledger audits by adding the key :code:`ledger` to the :code:`audit_types` config setting.

-----------
Order Audit
-----------

The order audit is an extra level of strictness in auditing. It compares the list of recent trades on a given exchange account recorded in our database to what the exchange API itself reports. If there is an order or trade on the exchange that isn't in our database, that might be a big problem: it could mean our account is compromised by an attacker, or it could mean that something's gone wrong in the Engine ledger maintenance, and an order has been placed but not recorded. 

You can enable order audits by adding the :code:`order` to the :code:`audit_types` setting.


3rd party logging
=================

.. _`Sentry`:  https://sentry.io/welcome/

Gryphon has support for sending exceptions and log output to `Sentry`_, for review and debugging purposes.

Enabling this feature is simple. Add your sentry root URL to the :code:`.env` under the key :code:`SENTRY_URL`. Then, add the flag :code:`--sentry` to the command line parameters when you run a strategy, or the line :code:`sentry: yes` to the :code:`platform` section of your strategy's :code:`.conf` file.

Feel free to tweak this parameter on and off as desired, for example, if you are testing changes to a strategy and don't want the log output recorded.

.. _monitoring:

Monitoring
==========

It's easy to set up monitoring for your strategies such that you can get a page if something goes wrong.

Monitoring in Gryphon usually proceeds by use of Heartbeats. These are files on the filesystem which correspond to critical system checks, and which contain the timestamp of the last moment when the system passed that check. In this way, they act like dead-mans-switches, where check-failure is the default, and for a check to pass, it must constantly be updated.

Strategy heartbeating can be turned on by adding the command line flag :code:`--heatbeat`, or equivalent configuration line :code:`heartbeat: yes`. Heartbeat files are kept in the relative directory :code:`monit/heartbeat/[strategy.name].txt`. The engine will touch this file every tick with the new timestamp.

.. _monit: https://mmonit.com/monit/documentation/monit.html
.. _Pagerduty: https://www.pagerduty.com/docs/guides/monit-integration-guide/

With heartbeats enabled, you can use a daemon like monit_ to monitor the heartbeats and call out to a 3rd party alerting service if a heartbeat fails. Pagerduty_ is a good choice.

Instrumentation
===============

The engine has built-in instrumentation features you can take advantage of.

You can use the :code:`Datum` table in the trading database to record simple key-value pair data for use by your strategies or later analysis. This can be done directly with the :py:class:`gryphon.lib.models.datum.DatumRecorder` utility class. For example:

   .. code-block:: python

      DatumRecorder().record('BITSTAMP_BTC_USD_MIDPOINT', Decimal('8122.38'))

:code:`Datums` can be optionally foreign-keyed to :code:`Orders` if you want to associate extra data to orders as well.

Utility functions for tracking tick execution speeds are also available in :py:mod:`gryphon.execution.lib.tick_profiling`.

Fast Market Data
================

The Gryphon Data Service is a standalone-executable that can feed high-performance market data into your strategies, massively speeding up execution times in some architectures. Installation and operation are non-trivial so we recommend following along with the article data_service_ to start out.

If you GDS installation is already complete, you can enable GDS data for all integrations by adding the flag :code:`--emerald` to the command line parameters, or add the line :code:`emerald: yes` to the :code:`platform` section of your :code:`.conf` file.
