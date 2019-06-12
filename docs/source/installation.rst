.. _installation:

============
Installation
============

Gryphon is currently tested on the following systems:

* Ubuntu 16.04
* MacOSX Sierra and later

Users who simply want access to the gryphon libraries for use in another project can
follow this document as far as `Install the library`_. Users who want to use gryphon for
trading should continue through `Set up the trading harness`_. For advanced
installations see :ref:`dashboards` and :ref:`data_service`.

Ubuntu 16.04
============

.. _library-install:

Install the library
-------------------

#. First make sure you have the prerequisites: python2.7, pip, and mysqlclient.

   .. code-block:: bash

      sudo apt update
      sudo apt install python2.7 python-pip libmysqlclient-dev

.. _virtualenv: https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv

#. While technically optional, we highly recommend that you use virtualenv_ to create an isolated python environment in which to install Gryphon.

#. Install the gryphon package. You can install the latest version hosted in the python package index using pip.

   .. code-block:: bash

      pip install gryphon

#. Gryphon installs a command line tool for running it's unit test suite. It's good practice to run it at this stage.

   .. code-block:: bash

      gryphon-runtests

The test runner will trigger a build of some of gryphon's cython modules, which may take
2-3 minutes. During the build you might see a lot of cython log output--don't worry,
this is normal. Afterwards, you'll hopefully see a long row of green dots indicating a
successful test run.

At this stage, you can use many features of gryphon as a software library in other
projects, but running strategies themselves requires a few more setup steps.


Set up the trading harness
--------------------------

The trading harness is the executable that runs trading strategies. It's installed in
the PATH as :code:`gryphon-exec`. It has a few more dependencies than the pure library.

#. Install memcached

   .. code-block:: bash

      sudo apt install memcached libmemcached-dev zlib1g-dev


#. Start a new mysql database and make it accessible to the machine you are running gryphon from. Create a user for gryphon with all read/write privileges to this database.

#. Gryphon uses .env files to keep sensitive credentials on your machine. Please read :ref:`dotenv_files` to learn more about this and best practices. For now, create a file in your current working directory named '.env', and add the mysql url for your new database to it as follows:

   .. code-block:: bash

      TRADING_DB_CRED=mysql://[username]:[password]@[database_host]:3306/[database_name]

#. Now migrate the database to the latest gryphon schema. This can be done with a script in the trading harness.

   .. code-block:: bash

      gryphon-exec run-migrations --database trading --execute

That's it! At this point you should be ready to move on to :ref:`use_for_trading` to
start running strategies.

MacOS
=====

The installation steps for OSX are the same as for ubuntu, but instead of aptitude, use Homebrew_ to install prerequisites as follows.

.. _Homebrew: https://brew.sh/

   .. code-block:: bash
      
      brew install python@2
      brew install mysql
      brew install memcached

The rest of the steps are identical to those for Ubuntu 16.04.

.. _`stackoverflow answer`: https://stackoverflow.com/questions/12218229/my-config-h-file-not-found-when-intall-mysql-python-on-osx-10-8

Some MacOS users have had issues installing mysql using :code:`brew`. This `stackoverflow answer`_ provides a functioning fix.


