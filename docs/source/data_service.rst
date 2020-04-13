.. _data_service:

==========================
Gryphon Data Service (GDS)
==========================

.. _`RabbitMQ`: https://www.rabbitmq.com/

The Gryphon Data Service is astandalone executable that ingests high performance market data from the exchanges, feeds it to running strategies, and optionally archives it for later use in quantitative analysis or machine learning. Built in a producer-consumer model using `RabbitMQ`_, it's the most powerful upgrade your strategies can get.

.. _gds_installation:

Installation
============

To run the data service you must install gryphon from source, you cannot use the built distributions in pypi. To do this, follow the same steps in :ref:`library-install`, but instead of :code:`pip install gryphon`, clone the repo from github and install the folder with the :code:`-e` flag.

   .. code-block:: bash
    
      mkdir gryphon && cd gryphon
      git clone git@github.com:TinkerWork/gryphon.git
      pip install -e .

GDS has it's own library requirements which are kept in a requirements file. From the root of your source directory, install them with:

   .. code-block:: bash
    
      pip install -r requirements/gryphon+gds.txt

Now, install redis and RabbitMQ. On Ubuntu this is done with aptitude as follows:

   .. code-block:: bash

      sudo apt-get install redis-server
      sudo apt-get install rabbitmq-server

On OSX, use :code:`brew`:

   .. code-block:: bash

      brew install redis
      brew install rabbitmq

Finally, install :code:`foreman`.

   .. code-block:: bash

      gem install foreman

At this point you should be able to cd into the :code:`gryphon/data_service` directory and try to start GDS with the command:

   .. code-block:: bash
    
      foreman start

This will not succeed, as you have not set up your GDS :code:`.env` yet, but that's our next step.

.. _gds_dotenv:

Data Service .env
-----------------

.. _`Configure Redis`: https://redis.io/topics/config
.. _`Configure RabbitMQ`: https://www.rabbitmq.com/networking.html

The minimum contents of you data service :code:`.env` are as follows:

   .. code-block:: bash

    GDS_DB_CRED=
    EXCHANGE_RATE_APP_ID=
    REDIS_URL=

    AMPQ_ADDRESS=
    AMPQ_USER=
    AMPQ_PASS=
    AMPQ_HOST=
    AMPQ_PORT=

You can find the appropriate settings for redis in their documentation, at `Configure Redis`_ and the same for the AMPQ settings at `Configure RabbitMQ`_.


