# from http://stackoverflow.com/a/952952/2208702
def flatten(l):
    return list([item for sublist in l for item in sublist])

def distinct(iterable, keyfunc=None):
    seen = set()
    for item in iterable:
        key = item if keyfunc is None else keyfunc(item)
        if key not in seen:
            seen.add(key)
            yield item
