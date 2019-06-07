.. _contributing:

=======================
Contributing to Gryphon
=======================

Gryphon is in active development and contributions are welcome and encouraged!

Pull Request Checklist
======================

Before submitting a PR, make sure you've done the following:

- Changes adhere to the :ref:`style_guide`
- Changes pass the existing unit tests, :code:`gryphon-runtests`
- Include new unit tests for your changes

Current Focus
=============

Gryphon can always use effort put into stability and code-quality. Here are some specific ideas on how to contribute to that area:

- Increase the number of unit tests and scope of test coverage
- Add docstrings and comments to existing modules
- Refactor existing modules to conform to the :ref:`style_guide` and pass :code:`flake8` tests
- Add sphinx documentation for complex features

Some more ambitious options for an interested engineer:

- Add a mechanism to track our test-coverage
- Improve our unit testing framework so we don't require exchange credentials to directly test strategies and exchange integrations
