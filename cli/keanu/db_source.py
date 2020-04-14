from .data_store import DataStore

class DBSource(DataStore):
    def __init__(_, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)

        _.schema = db_spec.get('schema', None)
        _.url = db_spec.get('url', None)
        _.local = _.url is None

        if not _.local:
            _.engine = db.get_engine(_.url, _.dry_run)

    def connection(_):
        if not _.local:
            conn = db.get_connection(_.engine)
        else:
            conn = _.batch.destination.connection()

        return conn

    def environ(_):
        env = {}
        if _.schema:
            env['SOURCE'] = _.schema
        return env

    def table(_, table):
        if _.schema:
            return '{}.{}'.format(_.schema, table)
        else:
            return table
