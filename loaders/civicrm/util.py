from sqlalchemy import text, bindparam
from sqlalchemy.schema import Table, MetaData
IGNORE=True


def ranges(points_gen, last=None):
    try:
        a1 = points_gen[0]
    except IndexError:
        return None

    for a2 in points_gen[1:]:
        yield (a1, a2)
        a1 = a2

    if last is not None:
        yield (a1, last)

def nest_sql(container, **nested):
    """Helper function to be able to nest one SQL TEXT in another, and if they
    have bound parameters (eg. "WHERE id = :foo", and "foo" bind-param is
    already defined using bindparams method), they will be copied to the
    resulting SQL.

    This is can be useful in parametrization of some queries: you can pass a subquery if its arguments as parameter.

    """
    # paste nested SQL into container SQL
    merged = container.format(**nested)
    # and wrap in TEXT object
    merged = text(merged)

    # now bind the nested SQL paramters into that container TEXT
    for k,n in nested.items():
        # # if any of these parameters is marked for expanding,
        # # configure it using bandparam(...expanding=True) on the TEXT
        # for par in map(lambda b: b.key, n.get_children()):
        #     if par in expanding:
        #         merged = merged.bindparams(bindparam(par, expanding=True))
        # then bind the parameters
        merged = merged.bindparams(*n.get_children())
    
    return merged


def get_table(conn, table_name):
    """
Fetches SQLAlchemy Table objects used to bulk insert.
    """
    meta = MetaData(conn)
    table = Table(table_name, meta, autoload=True)
    return table
