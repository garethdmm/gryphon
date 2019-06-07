.. _style_guide:

==================
Python Style Guide
==================

.. _`this introduction`: http://python.net/~goodger/projects/pycon/2007/idiomatic/handout.html

If you are new to python style, we recommend reading `this introduction`_.

.. _PEP8: https://www.python.org/dev/peps/pep-0008/
.. _`Google Python Style Guide`: https://google.github.io/styleguide/pyguide.html

Gryphon style follows `PEP8`_ and the `Google Python Style Guide`_ by default, with certain extra rules.

Always run :code:`flake8` on new files from the root gryphon package directory (to pick up the project's :code:`setup.cfg`). It should pass without errors. If an error shows up that disagrees with this style guide, discuss and consider adding it to flake8's ignore list


Use cdecimal.Decimal, not naked scalar values
---------------------------------------------

:code:`Decimal` is superior to python's built-in float class for handling high-precision numbers. Never use naked floats, unless comparing a :code:`Decimal` or :code:`Money` against zero, which is well defined.

When creating :code:`Decimal` objects, use quotes around the scalar value. This might seem odd at first but is critical to preventing difficult-to-diagnose bugs.

.. code-block:: python

    # Yes:
    spread = Decimal('0.004')

    # No no no, asking for trouble:
    spread = Decimal(0.004)

Use Money Objects for quantities of an asset
--------------------------------------------

When working with currency or asset quantities, use :py:class:`gryphon.lib.money.Money`.

Equivalently to :code:`Decimal`, always use quotes around the quantity when defining :code:`Money` objects. Write the currency code in uppercase.

.. code-block:: python

    # Yes:
    order_volume = Money('10', 'ETH')

    # Nope, never. 
    order_volume = Money(10, 'ETH')
    order_volume = Money('10', 'eth')

Line Length
-----------

90 characters. Set your terminal/editor at 92/93 characters width if you are using line numbers.

Whitespace
----------
4-space soft tabs, no trailing whitespace at end of lines or on empty lines. Newlines at end of files

Multi-lining function definitions
---------------------------------

The current style is to just keep it all on one line and ignore the character limit. TODO: Figure out something better.

Multiline Conditionals
----------------------

.. code-block:: python

    if ("order not found" in error_string
            or "order already done" in error_string):
        raise CancelOrderNotFoundError()

We break the line before the binary operator. Many sources use the opposite but we prefer to keep the operator nearer it's right operand. More explanation: https://www.python.org/dev/peps/pep-0008/#should-a-line-break-before-or-after-a-binary-operator

Use English Style in comments
-----------------------------

.. _`The Elements of Style`: http://www.gutenberg.org/ebooks/37134

Comments should more or less follow valid english grammar and syntax, including periods at the end of sentences and capitalized first letters. Follow english style described in: `The Elements of Style`_.

Docstrings
----------

Most methods should have them. They describe the purpose of the method or class, and how to use it.

.. code-block:: python

    def message_dev(dev):
        """Send the dev a checkin message on hipchat."""

    def message_dev(dev):
        """
        Send the dev a checkin message on hipchat.

        [... more details about how to use this function]
        """

Block comments
--------------

.. code-block:: python

    # This is a block comment.
    # It can go onto a new line when it makes sense, or after
    # hitting the 90 character limit.

Blank lines
-----------

Follow google. Two blank lines between top-level definitions, be they function or class definitions. One blank line between method definitions and between the class line and the first method.

Use blank lines around logical blocks of code and especially condition blocks.

Imports
-------

Follow google, with sections for stdlib, 3rd party, and gryphon imports, separated by newlines.

.. code-block:: python

    import os
    import time

    import delorean

    from gryphon.lib import configuration
    from gryphon.lib.exchange import order_types

Do not use function imports.

String Quotes
-------------

Only single quotes.

Deprecated Functions
--------------------

Delete them.

File encoding
-------------

Add `# -*- coding: utf-8 -*-` only if the file contains utf-8 characters

