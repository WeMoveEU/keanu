import collections

IGNORE=True

def prop_loader():
    from keanu import config
    batch = config.build_batch({}, config.configuration_from_argument("."))
    script = collections.namedtuple('Script', ['source', 'destination'])
    l = script(batch.sources[0], batch.destination)
    return l
