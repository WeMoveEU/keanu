from . import db


class DataStore:
    """
    Arguments:

    name - name for the store
    db_spec - connection specification

    Parameters:

    dry_run - do not really execute reads or writes on store

    Properties set by constructor

    spec
    batch
    url
    local

    if not local: engine

    """

    def __init__(self, name, db_spec, dry_run=False):

        self.name = name
        self.local = False
        self.spec = db_spec
        self.dry_run = dry_run
        self.batch = None

        # schema and connection are used in DataStore,
        # they should be moved there
        self.schema = db_spec.get("schema", None)
        self.url = db_spec.get("url", None)
        self.local = self.url is None

        if not self.local:
            self.engine = db.get_engine(self.url, self.dry_run)

    def set_batch(self, b):
        self.batch = b

    def connection(self):
        if not self.local:
            return db.get_connection(self.engine)

        return self.batch.destination.connection()

    def use(self):
        self.connection().execute("USE {}".format(self.schema))
