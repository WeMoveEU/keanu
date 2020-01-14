from .data_store import DataStore

class DBSource(DataStore):
    def __init__(_, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)
        _.conn = None
        _.local = 'url' not in db_spec
        _.schema = db_spec.get('schema', None)

    def connection(_):
        if _.conn is None:
            if not _.local:
                _.conn = db.get_engine(_.url, _.dry_run).connect()
            else:
                _.conn = _.batch.destination.connection()
        return _.conn

    def environ(_):
        env = {}
        if _.schema:
            env['SOURCE'] = _.schema
        return env
