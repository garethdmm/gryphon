from gryphon.lib.money import Money

from collections import defaultdict

class Position(dict):
    def __missing__(self, key):
        value = self[key] = Money(0, key)
        return value

class Brain(object):
    def __init__(self):
        pass

    def __repr__(self):
        return str(self)
    def __str__(self):
        return str(self.__dict__)
