from .data_store import DataStore


class DBSource(DataStore):
    def __init__(self, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)

    def environ(self):
        env = {}
        if self.schema:
            env["SOURCE"] = self.schema
        return env

    def table(self, table):
        if self.schema:
            return "{}.{}".format(self.schema, table)
        else:
            return table
