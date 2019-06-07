.. _ledger:

==================
Ledger Maintenance
==================

Maintaining a consistent ledger of your trading activity is vital to the long-term health of your business. Here are a few tools and methods you can use to make sure that your ledger is healthy.

Manual Trade Accounting
=======================

You can manually add orders and trades to the trading database with this command:

.. code-block:: bash

    gryphon-exec manual [exchange pair name] [exchange order id]
        --actor [strategy actor name]
        [--execute]

This script queries the exchange API for information about the order, any associated trades, and adds them to the trading database. This command can be run for orders that are already in the database as well and the information will be updated.

:code:`actor` is a string that identifies the entity that created this order. This usually refers to an algorithmic strategy. By default, strategies' :code:`actor` is their class name uppercased, although some strategies override this and define their own actor. Make sure you have the corrent string identifier here or the trades will not be included in the strategy's trade history, p&l, and position.

You can also use this tool to add trades made by human traders in the database. One approach is to give every human their own :code:`actor`, and account for their trades using that designation. In this scheme every human trader could even have their own :ref:`dashboard_tour_strategy`. You may also simply want to use a single :code:`actor` for all manual trades, such as 'MANUAL'.

Manual Deposits/Withdrawals
===========================

You can add deposit or withdrawal transactions to the ledger when you move cryptocurrency funds between accounts with this command:

.. code-block:: bash

    gryphon-exec withdraw [withdraw_exchange_name] [deposit_exchange_name] [amount]\
        [--execute]

Both :code:`withdraw_exchange_name` and :code:`deposit_exchange_name` must have initialized ledgers in the trading database. :code:`amount` must be a money-parsable string such as 'BTC 3.55'.

There is an equivalent command for fiat currency movements:

.. code-block:: bash

    gryphon-exec withdrawfiat [withdraw_exchange_name] [deposit_exchange_name] [amount]\
        [external_transaction_id]\
        [destination_amount]\
        [--execute]

This operates similarly to the :code:`withdraw` command, except you can add an :code:`external_transaction_id` such as a wire confirmation number for later reference, and a :code:`destination_amount`, which may be useful if the funds will be converted between currencies while in transit.

Debugging Issues
================

Debugging ledger mismatches can be an involved process, but there are a few recommendations we can make.

:ref:`auditing` can catch most issues within minutes of occurrence, which makes identifying the source of a mismatch much easire. Just imagine combing over a week of trading data looking for an error vs. five minutes of trading data.

As well, audit records are stored in the trading database, so you can find the last audit that passed, and the first audit that failed, and that will give you a time window in which the issue occurred.

The :ref:`dashboard_tour_ledger` displays a human-readable version of the ledger for a particular exchange account. Most exchanges give a similar page or csv export, with a time window properly identified, you can compare the exchange against this dashboard and find the error in a reasonable amount of time.

Manual Balance Adjustments
==========================

If it becomes necessary to add an arbitrary adjustment to an exchange ledger, this can be done by adding a :code:`Transaction` to the ledger in the amount of the adjustment. For a postive change, add a deposit, for a negative change add a withdrawal. We recommend adding a note in the :code:`transaction_details` dictionary explaining the purpose of the adjustment for later reference. Creating this adjustment can be done manually in :code:`gryphon-cli`.

For testing purposes, there is also a command line function to forcibly re-align the state in the trading database with the state reported by the exchange API. The command is this:

.. code-block:: bash

    gryphon-exec script reset_balance\
        --exchange_name [exchange_pair_name]\
        [--execute]

This script is located at :py:mod:`gryphon.execution.scripts.reset_balance`. When run, it will ask the exchange for it's current balance, set the record in the :code:`Exchange` table to that amount, and add a :code:`Transaction` to the ledger in the amount of the difference.

We recommend not making a habit of this in production, even though it might be tempting to do so instead of debugging underlying issues. Bugs tend to re-occur, and if these adjustments end up totalling to a non-trivial sum your long term P&L and other metrics may become inaccurate.

