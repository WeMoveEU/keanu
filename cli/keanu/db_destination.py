from .data_store import DataStore
from . import db

class DBDestination(DataStore):
    def __init__(_, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)

        _.conn = None
        _.url = db_spec['url']
        _.schema = db.url_to_schema(_.url)

    def connection(_):
        if _.conn is None:
            if not _.local:
                _.conn = db.get_engine(_.url, _.dry_run).connect()
            else:
                src = _.batch.find_source(lambda s: s.local == False)
                _.conn = src.connection()
        return _.conn

    def environ(_):
        return {}
