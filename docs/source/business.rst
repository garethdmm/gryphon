.. _business:

============================
Business Management Features
============================


.. _really_use_audits:

Use Audits
==========

If you are using Gryphon to perform high-volume continuous-execution trading with large amounts of deployed assets, it is highly recommended that you enable :ref:`auditing` in your strategies at some frequency, joined with some form of :ref:`monitoring`.

This has a lot of benefits. The most important of which is it creates a strong guarantee that so long as no one's phone is ringing, everything is proceeding roughly according to plan. Even when small issues occur, having audits records to look back at will reduce the time cost of debugging by orders of magnitude.

.. _optimize_pl:

Optimizing non-trading P&L
==========================

Aside from the quality of your strategies, there are several other factors that affect your business's performance. In particular: exchange fees, asset transfer fees, operating expenses, and foreign exchange fluctuations. Finding methods of reducing the negative of any of these categories can frequently be more impactful than making strategy improvements. You'll find the :ref:`dashboard_tour_fund` gives an excellent overview of the components of your p&l over a given time window. 

Exchange fees and deposit/withdrawal fees are tracked in the ledger, and you can see a summary of them in the Fees Dashboard. It's common for a single exchange to be a majority of your fees, so visualizing this data helps identify problematic exchanges. You may choose to move more trading to other venues, or find ways of reducing your fees paid to that exchange. Deposit/withdrawal fees can be a similar story. If you are paying lot in deposit fees to a particular exchange, you may be able to change the deposit method, frequency, or other characteristics to achieve a better result.

In a large trading business you'll likely find yourself holding assets in several different currency denominations. The exchange rates of these currencies against your base currency (probably USD) could have a non-trivial effect on your bottom line. The Fund dashboard has a top-level metric to show this effect. It's important to be aware of this, and to reduce your exposure as much as possible if you find it to be an issue.

Creating a more lean business is also a perfectly valid way of increasing returns, in particular if you are able to re-invest those savings into profitable strategies. If you make use of the :ref:`bank_integration` feature of Gryphon, you'll be able to see this effect in your numbers and make appropriate decisions.

.. _ledger_export:

Financial Data Export
=====================

When doing financial reporting for taxes or other purposes, it's useful to be able to communicate the full ledger trading history to 3rd parties like accountants. It's unlikely these groups will accept a mysql database dump, so Gryphon includes a script to export the full ledger for an account in this format.

This is implemented at :py:mod:`gryphon.execution.scripts.ledger_export`, and can be called with this command:

.. code-block:: bash

    gryphon-exec script ledger_export\
      --exchange [exchange_account_name]\
      --start [start_time]\
      --end [end_time]\

Note that the start/end times should be strings in the ISO 8601 format.

This will write a file with the full ledger in it into the current directory into a descriptive filename. Be aware that for periods > 1 month, this may take a minute.

.. _investments:

Investment Tracking
===================

It is possible to represent investments into your business or fund within the trading database, giving you an even more detailed picture of your finances.

This is done with the :py:mod:`gryphon.lib.models.liability` table. When you take on a new investment, create a :code:`Liablity` object in the command line and commit it to the database.

Entries in this table are considered in the :py:mod:`gryphon.lib.assets` library which is used throughout the framework to calculate global p&l and other performance measures.

.. _bank_integration:

Bank Account Integration
========================

The trading database is designed to hold ledgers not just for your exchange accounts, but also your business bank accounts. By representing your business operating costs and transactions inside the trading database you can have a complete picture of your business's finances in one spot: something no exchange or bank can offer.

Here is an overview of the concepts and components to turning on a bank account integration. Note that, as an advanced feature, turning on a bank account integration can be an in-depth process.

Start a Bank Account ledger
---------------------------

The same as with any exchange account, we need an entry in the :code:`Exchange` table to track our bank account. Instead of using :code:`initialize-ledger` script to start this one, you'll have to create and commit the object manually. This isn't difficult, just familiarize yourself with the :py:class:`gryphon.lib.models.exchange.Exchange` object, create one at the command line using :code:`gryphon-cli`, and commit it.

There are no trades in a bank account ledger, only :code:`Transactions`. Debits to your bank account are :code:`WITHDRAWAL`'s and credits are :code:`DEPOSIT`'s. After you create the account object, using a similar process, add a :code:`DEPOSIT` transaction for the initial balance of the account to bring it's ledger balance into consistency.

Bank Account API Integration
----------------------------

In order to pull in line-items from your bank account, you'll need a way of interacting with your bank programmatically. If your bank provides API access in a similar way to an exchange, this is straightforward, and all you need to do is write a wrapper for the bank's API that allows you to poll for new line-items periodically. If your bank doesn't have API access, you can go deeper and write a tool that parses the HTML directly from your online banking.

Bank Bot
--------

Armed with your ledger and bank account integration, the last step is to run a process that periodically updates the bank account ledger in the trading database. Gryphon ships with a version of this you can adapt to your purposes in :py:mod:`gryphon.execution.bots.bank`. We recommend setting the process to run once an hour.

