import click
from . import config
from .sql_loader import SqlLoader
from glob import glob
from os import path
import unittest

current_config =  None

class BatchTestCase(unittest.TestCase):
    def __init__(_, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _.connection = None

    @property
    def config(_):
        return current_config

    def setUp(_):
        _.batch = _.load_all_fixtures()
        _.batch.destination.use()
        _.connection = _.batch.destination.connection()

        if hasattr(_, "ORDER"):
            _.full_load(_.ORDER)

    def full_load(_, order):
        batch = config.build_batch({'incremental': False, 'order': order}, _.config)

        for e,d in batch.execute():
            pass

    def incremental_load(_, order=None):
        if order is None:
            order = _.ORDER
        batch = config.build_batch({'incremental': True, 'order': order}, _.config)

        for e,d in batch.execute():
            pass

    def load_all_fixtures(_):
        mode = {}
        batch = config.build_batch(mode, _.config)

        for step in _.config:
            if 'destination' in step and 'fixtures' in step['destination']:
                _.load_fixtures(batch.destination, step['destination']['fixtures'])
            elif 'source' in step and 'fixtures' in step['source']:
                src = batch.find_source(lambda s: s.name == step['source']['name'])
                _.load_fixtures(src, step['source']['fixtures'])

        return batch

    def load_fixtures(_, db, fixtures):
        db.use()
        for fixture in fixtures:
            loader = SqlLoader(fixture, {}, None, db)
            loader.replace_sql_object('keanu', db.schema)
            for event, d in loader.execute():
                pass
                # if event.startswith('sql.script.start'):
                #     click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                #         loader.order,
                #         loader.filename,
                #         len(loader.lines),
                #         len(loader.statements)))


class TestLoaders():
    def __init__(_, configuration):
        super().__init__()
        _.config = configuration

    def run(_, directory, spec=None):
        global current_config
        current_config = _.config

        test_loader = unittest.TestLoader()

        pattern = spec or 'test*.py'
        suite = test_loader.discover(directory, pattern)

        unittest.TextTestRunner(verbosity=2).run(suite)

