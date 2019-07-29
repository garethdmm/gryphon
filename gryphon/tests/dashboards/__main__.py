"""
Main Module for this gryphon.tests.dashboards subpackage

This subpackage is runnable directly with :
`python -m gryphon.tests.dashboards`

This module is provided only for convenience for users convenience and for continuous integration,
mostly to record the options used for testing.

The output/results should be the same as if any one of these command line was run:
- `nosetests -s gryphon.tests.dashboards`
- `nosetests -s gryphon/tests/dashboards`
Most importantly the imports should behave the same.
"""
import nose

if __package__ is None:
    from gryphon.tests.dashboards import test_models
else:
    from . import test_models

if __name__ == '__main__':
    nose.runmodule(test_models.__file__)
