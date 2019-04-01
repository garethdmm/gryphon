def skipped(func):
    from nose import SkipTest
    def decorator(*args, **kwargs):
        raise SkipTest("Test %s is skipped" % func.__name__)
    decorator.__name__ = func.__name__
    return decorator
