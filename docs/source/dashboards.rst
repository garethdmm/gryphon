.. _dashboards:

==========
Dashboards
==========

Gryphon ships with a full suite of dashboards for managing your strategies and your
trading business. They exist in a webserver you can run locally or over the
internet so you can access them from anywhere.

.. _dashboard_installation:

Installation
============

.. _gryphon+dashboards.txt: https://github.com/TinkerWork/gryphon/blob/master/requirements/gryphon%2Bdashboards.txt

The dashboard server has some extra python requirements that the simple trading install
doesn't have. To install these, download the requirements file
`gryphon+dashboards.txt`_ from the gryphon github repository and run

.. code-block:: bash

    pip install -r gryphon+dashboards.txt

Next, create a new directory under your gryphon-root to hold your dashboard :code:`.env`
and any configuration files.

Set up for use with GDS Data
----------------------------

.. _dashboard_tour:

Tour
====

Trading Dashboard
-----------------

Ledger Dashboard
----------------

Orderbooks Dashboard
--------------------

Tradeview Dashboard
--------------------

Assets Dashboard
----------------

Balances Dashboard
------------------

.. _dashboard_customization:

Customization
=============


.. _dashboard_dotenv_reference:

Environment Variable Reference
==============================
