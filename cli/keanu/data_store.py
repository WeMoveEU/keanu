class DataStore:
    """
    name - name for the store
    local (boolean) - is this source local to some destination (like: same DB), or other way round?
    spec - connection specification
    dry_run - do not really execute reads or writes on store
    """
    def __init__(_, name, db_spec, dry_run=False):
        _.name = name
        _.local = False
        _.spec = db_spec
        _.dry_run = dry_run
        _.batch = None

    def set_batch(_, b):
        _.batch = b

    def use(_):
        _.connection().execute("USE {}".format(_.schema))
