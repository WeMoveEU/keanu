class DataStore:
    """
    name - name for the store
    local (boolean) - is this source local to some destination (like: same DB), or other way round?
    spec - connection specification
    dry_run - do not really execute reads or writes on store
    """
    def __init__(self, name, db_spec, dry_run=False):
        self.name = name
        self.local = False
        self.spec = db_spec
        self.dry_run = dry_run
        self.batch = None

    def set_batch(self, b):
        self.batch = b

    def use(self):
        self.connection().execute("USE {}".format(self.schema))
