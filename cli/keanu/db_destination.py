from .data_store import DataStore
from . import db

from sqlalchemy.orm import sessionmaker

class DBDestination(DataStore):
    def __init__(_, db_spec, name=None, dry_run=False):
        super().__init__(name, db_spec, dry_run)

        _.url = db_spec['url']
        _.schema = db.url_to_schema(_.url)
        if not _.local:
            _.engine = db.get_engine(_.url, _.dry_run)
            _.Session = sessionmaker(bind=_.engine)

    def connection(_):
        if not _.local:
            conn = db.get_connection(_.engine)
        else:
            src = _.batch.find_source(lambda s: s.local == False)
            conn = src.connection()
        return conn

    def session(_):
        if not _.local:
            return _.Session()
        # Not implemented
        return None

    def environ(_):
        return {}
