import unittest
from unittest import TestSuite
from collections import defaultdict

import click
from . import config, helpers, tracing
from .sql_loader import SqlLoader

current_config = None


def _batch_test(func, mode):
    "Annotate a function with mode (initial or incremental)"
    func._keanu_batchMode = mode
    return func


def initial_test(func):
    "Annotate function with initial mode"
    return _batch_test(func, "INITIAL")


def incremental_test(func):
    "Annotate function with incremental mode"
    return _batch_test(func, "INCREMENTAL")


def _fixture(func, source, load_after_step, depend_on=[]):
    """Annotate function with fixture metadata.

    :param int load_after_step: fixture will be loaded after given step - lets you inject some change in the middle of keanu batch
    :param source: source name in keanu config. The fixture will USE this db.
    :param depend_on: list of fixture methods of test case classes. Eg. TestAction.load_signatures
    """
    func._keanu_fixture = True
    func._keanu_source = source
    func._keanu_step = load_after_step
    func._keanu_deps = set([method.__qualname__ for method in depend_on])

    return func


def initial_fixture(source, load_after_step=0, depend_on=[]):
    "Decorate funcation with mode=initial and fixture metadata"

    def decorator(func):
        return initial_test(_fixture(func, source, load_after_step, depend_on))

    return decorator


def incremental_fixture(source, load_after_step=0, depend_on=[]):
    "Decorate funcation with mode=incremental and fixture metadata"

    def decorator(func):
        return incremental_test(_fixture(func, source, load_after_step, depend_on))

    return decorator


class BatchTestCase(unittest.TestCase):
    "A single test case (one file)"

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
        self.batch = config.build_batch({"display": True}, self.config)
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
        batch = config.build_batch(
            {"display": True, "incremental": True, "order": order}, self.config
        )

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
        "configuration is a keanu batch config"
        super().__init__()
        self.config = configuration

    def run(self, directory, pattern="test*.py"):
        global current_config
        current_config = self.config
        text_runner = unittest.TextTestRunner(verbosity=2)

        (initial_tests, incremental_tests) = self.discover_tests(directory, pattern)
        (initial_fixtures, incremental_fixtures) = self.discover_fixtures(
            directory, pattern
        )

        self.run_global_fixtures()
        self.initial_load(initial_fixtures, text_runner.stream)

        initial_result = text_runner.run(initial_tests)

        self.incremental_load(incremental_fixtures, text_runner.stream)

        incremental_result = text_runner.run(incremental_tests)

        return initial_result.wasSuccessful() and incremental_result.wasSuccessful()

    def discover_tests(self, directory, pattern, methodPrefix="test"):
        """
        Finds methods prefixed with test_ in all test classes.
        By passing methodPrefix="load", it will find fixtures instead.
        """
        test_loader = unittest.TestLoader()
        test_loader.testMethodPrefix = methodPrefix
        suite = test_loader.discover(directory, pattern)
        if test_loader.errors:
            raise Exception(
                "💥 Error while discovering {methodPrefix} functions:\n"
                + "\n".join(test_loader.errors)
            )
        return self.split_suite(suite)

    def discover_fixtures(self, directory, pattern):
        return map(
            lambda suite: self.map_steps(suite),
            self.discover_tests(directory, pattern, "load"),
        )

    def run_global_fixtures(self):
        """
        Run fixtures which are defined in the yaml file under fixtures: key of a source or destination
        """
        mode = {}
        batch = config.build_batch(mode, self.config)

        # Loaders expect to be within a tracing batch transaction
        with tracing.batch(batch):
            for step in self.config:
                if "destination" in step and "fixtures" in step["destination"]:
                    self.load_fixtures(
                        batch.destination, step["destination"]["fixtures"]
                    )
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

    def map_steps(self, fixtures):
        """
        Take fixtures and arrenge them in a mapping from step number to TestSuite object containing them,
        in order satisfying their interdependencies.

        Fixtures are methods of test case classes.

        They are annotated with
        - `_keanu_step` attribute, which is an integer representing the step number after which they should be run.
        - `_keanu_deps` attribute, which specifies a list of fixtures that should be run before this one.
        """

        def _scan_steps(fixtures, result={}):
            """Find all methods in a TestSuite hierarchy"""
            for fixture in fixtures:
                if isinstance(fixture, TestSuite):
                    _scan_steps(fixture, result)
                else:
                    method = getattr(fixture, fixture._testMethodName)
                    step = method._keanu_step
                    result[step].append(fixture)
            return result

        def _method(test):
            """We get test case classes with a _testMethodName to specify the test method"""
            return getattr(test, test._testMethodName)

        def _sort_by_deps(lst):
            """
            Sort the fixtures so that dependency fixtures for the same step are run first.
            List of dependencies is found in `_keanu_deps` attribute of each fixture.

            Arguments:
            :param list lst: -- a list of elements to sort
            """

            def is_satisfied(item, already_satisfied):
                return _method(item)._keanu_deps <= already_satisfied

            remain = set(lst)
            satisfied = set()
            while remain != set():
                ready = {item for item in remain if is_satisfied(item, satisfied)}
                for r in ready:
                    satisfied.add(_method(r).__qualname__)
                    yield r
                remain = remain - ready
                if ready == set() and remain != set():
                    raise RuntimeError(f"Cannot satisfy dependecies {remain}")

        result = defaultdict(lambda: [])
        _scan_steps(fixtures, result)

        return {k: TestSuite(_sort_by_deps(v)) for k, v in result.items()}

    def run_load(self, incremental, fixtures, stream):
        mode = "incremental" if incremental else "initial"
        if 0 in fixtures:
            self.run_test_fixtures(fixtures[0], stream, mode)
        click.echo(f"🚚 Performing {mode} load...")
        batch = config.build_batch({"incremental": incremental}, self.config)
        steps_run = set()
        for event, data in batch.execute():
            scr = data["script"]
            if (
                event.endswith("script.end")
                and scr.order in fixtures
                and scr.order not in steps_run
            ):
                self.run_test_fixtures(
                    fixtures[scr.order], stream, "post-step " + str(scr.order)
                )
                steps_run.add(scr.order)

    def initial_load(self, fixtures, stream):
        self.run_load(False, fixtures, stream)

    def incremental_load(self, fixtures, stream):
        self.run_load(True, fixtures, stream)

    def run_test_fixtures(self, fixtures, stream, mode):
        click.echo("🚚 Loading {} fixtures...".format(mode))
        result = unittest.TextTestResult(stream, True, verbosity=1)
        fixtures.run(result)
        if result.errors:
            raise Exception(
                "💥 Error(s) while loading fixtures:\n"
                + "\n".join(map(lambda e: e[1], result.errors))
            )
        else:
            click.echo("")
