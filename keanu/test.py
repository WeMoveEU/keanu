import unittest
from unittest import TestSuite


import click
from . import config, helpers
from .sql_loader import SqlLoader

current_config = None

def batch_test(mode, func):
    func._keanu_batchMode = mode
    return func

def initial_test(func):
    return batch_test("INITIAL", func)

def incremental_test(func):
    return batch_test("INCREMENTAL", func)

def incremental_fixture(source):
    def decorator(func):
        func._keanu_fixture = True
        func._keanu_source = source
        return incremental_test(func)
    return decorator

class BatchTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_order = 0
        self.connection = None

    @property
    def config(self):
        return current_config

    @property
    def _source(self):
        testMethod = getattr(self, self._testMethodName)
        return testMethod._keanu_source

    def setUp(self):
        self.batch = config.build_batch({}, self.config)
        if self._is_fixture():
            sourcedb = self.batch.find_source_by_name(self._source)
            sourcedb.use()
            self.connection = sourcedb.connection()
        else:
            self.batch.destination.use()
            self.connection = self.batch.destination.connection()

    def incremental_load(self, order=None):
        if order is None:
            order = self.default_order
        batch = config.build_batch({"incremental": True, "order": order}, self.config)

        for _ in batch.execute():
            pass

    def _is_incremental(self):
        testMethod = getattr(self, self._testMethodName)
        return getattr(testMethod, "_keanu_batchMode", "INITIAL") == "INCREMENTAL"

    def _is_fixture(self):
        testMethod = getattr(self, self._testMethodName)
        return getattr(testMethod, "_keanu_fixture", False)


class TestRunner:
    """Orchestrate the discovery and running of tests using unittest classes"""

    def __init__(self, configuration):
        super().__init__()
        self.config = configuration

    def run(self, directory, pattern='test*.py'):
        global current_config
        current_config = self.config
        text_runner = unittest.TextTestRunner(verbosity=2)

        (initial_tests, incremental_tests) = self.discover_tests(directory, pattern)
        (initial_fixtures, incremental_fixtures) = self.discover_fixtures(directory, pattern)

        self.run_global_fixtures()
        self.run_fixtures(initial_fixtures, text_runner.stream, "initial")
        self.initial_load()

        text_runner.run(initial_tests)

        self.run_fixtures(incremental_fixtures, text_runner.stream, "incremental")
        self.incremental_load()

        text_runner.run(incremental_tests)

    def discover_tests(self, directory, pattern, methodPrefix="test"):
        test_loader = unittest.TestLoader()
        test_loader.testMethodPrefix = methodPrefix
        suite = test_loader.discover(directory, pattern)
        return self.split_suite(suite)

    def discover_fixtures(self, directory, pattern):
        return self.discover_tests(directory, pattern, "load")

    def run_global_fixtures(self):
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

    def split_suite(self, suite):
        """Split the given test suite into a initial suite and incremental suite"""
        initial = TestSuite()
        incremental = TestSuite()
        for test in suite:
            if isinstance(test, TestSuite):
                (sub_initial, sub_incremental) = self.split_suite(test)
                initial.addTest(sub_initial)
                incremental.addTest(sub_incremental)
            elif isinstance(test, BatchTestCase) and test._is_incremental():
                incremental.addTest(test)
            else:
                initial.addTest(test)

        return (initial, incremental)

    def run_load(self, incremental):
        click.echo("🚚 Performing {} load...".format("incremental" if incremental else "initial"))
        batch = config.build_batch({"incremental": incremental}, self.config)
        for _ in batch.execute():
            pass

    def initial_load(self):
        self.run_load(False)

    def incremental_load(self):
        self.run_load(True)

    def run_fixtures(self, fixtures, stream, flavor):
        click.echo("🚚 Loading {} fixtures...".format(flavor))
        fixtures.run(unittest.TextTestResult(stream, True, verbosity=1))
        click.echo("")
