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
        _.transaction = None
        _.connection = None

    @property
    def config(_):
        return current_config

    def full_load(_, order):
        batch = config.build_batch({'incremental': False, 'order': order}, _.config)
        if _.transaction is None:
            _.connection = batch.destination.connection()
            _.transaction = _.connection.begin()

        for e,d in batch.execute():
            pass

    def tearDown(_):
        if _.transaction is not None:
            _.transaction.rollback()


class TestLoaders():
    def __init__(_, configuration):
        super().__init__()
        _.config = configuration

    def set_up(_):
        mode = {
            'incremental': False
        }

        batch = config.build_batch(mode, _.config)

        for step in _.config:
            if 'destination' in step and 'fixtures' in step['destination']:
                _.load_fixtures(batch.destination, step['destination']['fixtures'])
            elif 'source' in step and 'fixtures' in step['source']:
                src = batch.find_source(lambda s: s.name == step['source']['name'])
                _.load_fixtures(src, step['source']['fixtures'])

        return batch

    def load_fixtures(_, db, fixtures):
        for fixture in fixtures:
            loader = SqlLoader(fixture, {}, None, db)
            loader.replace_sql_object('keanu', db.schema)
            for event, d in loader.execute():
                if event.startswith('sql.script.start'):
                    click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                        loader.order,
                        loader.filename,
                        len(loader.lines),
                        len(loader.statements)))

    def run(_, directory, spec=None):
        global current_config
        current_config = _.config

        batch = _.set_up()

        test_loader = unittest.TestLoader()

        if spec is None:
            suite = test_loader.discover(directory)
        else:
            suite = test_loader.loadTestsFromNames(spec)

        unittest.TextTestRunner(verbosity=2).run(suite)

