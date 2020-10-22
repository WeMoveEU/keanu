import unittest


import click
from . import config, helpers
from .sql_loader import SqlLoader

current_config = None


class BatchTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_order = 0
        self.connection = None

    @property
    def config(self):
        return current_config

    def setUp(self):
        self.batch = config.build_batch({}, self.config)
        self.batch.destination.use()
        self.connection = self.batch.destination.connection()

    def incremental_load(self, order=None):
        if order is None:
            order = self.default_order
        batch = config.build_batch({"incremental": True, "order": order}, self.config)

        for _ in batch.execute():
            pass


class TestLoaders:
    def __init__(self, configuration, no_fixtures):
        super().__init__()
        self.config = configuration
        self.no_fixtures = no_fixtures

    def run(self, directory, spec=None):
        global current_config
        current_config = self.config

        if not self.no_fixtures:
            self.load_all_fixtures()
            self.full_load()

        test_loader = unittest.TestLoader()

        pattern = spec or "test*.py"
        suite = test_loader.discover(directory, pattern)

        return unittest.TextTestRunner(verbosity=2).run(suite)

    def load_all_fixtures(self):
        mode = {}
        batch = config.build_batch(mode, self.config)

        for step in self.config:
            if "destination" in step and "fixtures" in step["destination"]:
                self.load_fixtures(batch.destination, step["destination"]["fixtures"])
            elif "source" in step and "fixtures" in step["source"]:
                src = batch.find_source(lambda s: s.name == step["source"]["name"])
                self.load_fixtures(src, step["source"]["fixtures"])

        return batch

    def load_fixtures(self, db, fixtures):
        db.use()
        for fixture in fixtures:
            click.echo("🚚 Loading fixture {}...".format(fixture))
            if not fixture.endswith(".sql"):
                fixture = helpers.schema_path(fixture)
            loader = SqlLoader(fixture, {}, None, db)
            loader.replace_sql_object("keanu", db.schema)
            for _ in loader.execute():
                pass

    def full_load(self):
        click.echo("🚚  Perform full initial load...")
        batch = config.build_batch({"incremental": False}, self.config)
        for _ in batch.execute():
            pass
