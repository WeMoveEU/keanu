from .data_store import DataStore

class DBSource(DataStore):
    def __init__(self, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)

        self.schema = db_spec.get('schema', None)
        self.url = db_spec.get('url', None)
        self.local = self.url is None

        if not self.local:
            self.engine = db.get_engine(self.url, self.dry_run)

    def connection(self):
        if not self.local:
            conn = db.get_connection(self.engine)
        else:
            conn = self.batch.destination.connection()

        return conn

    def environ(self):
        env = {}
        if self.schema:
            env['SOURCE'] = self.schema
        return env

    def table(self, table):
        if self.schema:
            return '{}.{}'.format(self.schema, table)
        else:
            return table
