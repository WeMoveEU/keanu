from dotenv import load_dotenv
load_dotenv()

import click
from click_aliases import ClickAliasedGroup
import json
from glob import glob
from os import environ
from . import db, util, metabase, config, helpers
from .sql_loader import SqlLoader
from .db_destination import DBDestination
from .test import TestLoaders
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
import re
import sys
import traceback
import logging


@click.group(cls=ClickAliasedGroup)
def cli():
    pass

def positive_int(ctx, param, value):
    v = int(value)
    if v >= 1:
        return v
    else:
        raise click.BadParameter("-t thread_number must be a positive integer")

@cli.command(aliases=['l'])
@click.option('-i', '--incremental', is_flag=True, default=False, help='incremental load')
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default='0:', help='specify order of files to run by (eg. 10 or 10,12 or 10:15,60 etc)')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
@click.option('-t', '--threads', default=1, callback=positive_int, help='Number of threads for parallel python scripts')
@click.option('-v', '--verbose', is_flag=True, default=False, help="More logging")
@click.argument('config_or_dir', default='keanu.yaml', type=click.Path(exists=True))
def load(incremental, order, dry_run, display, warn, threads, config_or_dir, verbose):
    set_verbose(verbose)
    mode = { 'incremental': incremental,
             'order': order,
             'display': display,
             'warn': warn,
             'order': order,
             'dry_run': dry_run,
             'rewind': False,
             'threads': threads }

    configuration = config.configuration_from_argument(config_or_dir)
    batch = config.build_batch(mode, configuration)

    for event, data in batch.execute():
        scr = data['script']
        if event.startswith('sql.script.start'):
            click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                scr.order,
                scr.filename,
                len(scr.lines),
                len(scr.statements)))

        elif event.startswith('sql.statement.start'):
                click.echo("📦 {0}...".format(
                    util.highlight_sql(
                        scr.statement_abbrev(data['sql']))),
                           nl=display)

        elif event.startswith('sql.statement.end'):
            code = util.highlight_sql(scr.statement_abbrev(data['sql']))

            # If display (-d) is set, the code was already shown on start,
            # and we are not overwriting the same line
            if display:
                code = ''

            click.echo("\r✅️ {} rows in {:0.2f}s {:}".format(
                data['result'].rowcount,
                data['time'],
                code
            ))

        elif event.startswith('py.script.start'):
            click.echo("🐍 [{:3d}] {}".format(
                scr.order,
                scr.filename),
                       nl=(display or dry_run))

        elif event.startswith('py.script.end'):
            click.echo("\r✅ [{:3d}] {} in {:0.2f}s".format(
                scr.order,
                scr.filename,
                data['time']
            ))




@cli.command(aliases=['d'])
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default='0:', help='specify order of files to run by (eg. 10 or 10,12 or 10:15,60 etc)')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
@click.argument('config_or_dir', default='keanu.yaml', type=click.Path(exists=True))
def delete(order, display, dry_run, warn, config_or_dir):
    mode = {
        'order': order,
        'display': display,
        'dry_run': dry_run,
        'warn': warn,
        'rewind': True }
    configuration = config.configuration_from_argument(config_or_dir)
    batch = config.build_batch(mode, configuration)

    for event, data in batch.execute():
        scr = data['script']
        if event.startswith('sql.script.start'):
            click.echo("🚒️ [{:3d}] {} ({})".format(
                scr.order,
                scr.filename,
                ', '.join(map(lambda s: s.rstrip(), map(util.highlight_sql, scr.deleteSql)))),
                       color=True)
        elif event.startswith('sql.statement.start'):
            click.echo("🔥 {0}".format(util.highlight_sql(scr.statement_abbrev(data['sql']))))
        elif event.startswith('py.script.start'):
            click.echo("💨 [{:3d}] {}".format(
                scr.order,
                scr.filename))



@cli.command(aliases=['s'])
@click.option('-D', '--drop', is_flag=True, default=False, help='DROP TABLEs before running the script')
@click.option('-L', '--loads', default=[], multiple=True, help='Load this SQL file')
@click.option('-H', '--helper', default=[], multiple=True, help='Load this helper SQL')
@click.argument('database_url')
def schema(drop, loads, helper, database_url):
    dest = DBDestination({'url': environ['DATABASE_URL']})
    connection = dest.connection()

    if drop:
        for (table, _) in connection.execute("show full tables where Table_Type = 'BASE TABLE'"):
            connection.execute('SET FOREIGN_KEY_CHECKS = 0')
            click.echo('💥 Dropping table {}'.format(table))
            connection.execute('DROP TABLE {}'.format(table))

    loads = [helpers.schema_path(x) for x in helper] + list(loads)

    if loads:
        for load in loads:
            script = SqlLoader(load, {}, None, dest)
            script.replace_sql_object('keanu', dest.schema)
            click.echo("🚚 Loading {}...".format(script.filename))
            with connection.begin() as tx:
                for event, data in script.execute():
                    scr = data['script']
                    if event.startswith('sql.statement.start'):
                        click.echo("📦 {0}...".format(
                            util.highlight_sql(
                                scr.statement_abbrev(data['sql']))),
                                   nl=False)
                    elif event.startswith('sql.statement.end'):
                        click.echo("\r✅️ {} rows in {:0.2f}s {:}".format(
                            data['result'].rowcount,
                            data['time'],
                            util.highlight_sql(scr.statement_abbrev(data['sql']))
                        ))

@cli.group('metabase', cls=ClickAliasedGroup, aliases=['mb'])
def metabase_cli():
  pass

@metabase_cli.command('export', aliases=['e'])
@click.option('-c', '--collection', help="Name of the collection to export")
@click.option('-j', '--json-file', default=None, help="path to JSON file to import")
@click.option('-y', '--yaml-dir', default=None, help="path to directory with yaml files")
@click.option('-v', '--verbose', is_flag=True, default=False, help="More logging")
def metabase_export(collection, json_file, yaml_dir, verbose):
    set_verbose(verbose)
    client = metabase.Client()
    mio = metabase.MetabaseIO(client)
    result = mio.export_json(collection)
    if json_file:
        with open(json_file, 'w') as out:
            out.write(json.dumps(result, indent=2, sort_keys=True))
    if yaml_dir:
        splitter = metabase.Splitter(yaml_dir)
        splitter.store(result)
    if not (json_file or yaml_dir):
        print(json.dumps(result, indent=2, sort_keys=True))

@metabase_cli.command('import', aliases=['i'])
@click.option('-c', '--collection', help="Name of the collection to import into")
@click.option('-j', '--json-file', default=None, help="path to JSON file to import")
@click.option('-y', '--yaml-dir', default=None, help="path to directory with yaml files")
@click.option('-m', '--metadata', is_flag=True, help="Also import metadata before importing the collection")
@click.option('-o', '--overwrite', is_flag=True, help="Overwrite cards")
@click.option('-D', '--db-map', multiple=True, help="Map Metabase database names fromname:toname.")
@click.option('-V', '--validate', is_flag=True,help="Validate JSON before load")
@click.option('-v', '--verbose', is_flag=True, default=False, help="More logging")
def metabase_import(collection, json_file, metadata, overwrite, db_map, validate, yaml_dir, verbose):
    set_verbose(verbose)
    client = metabase.Client()
    mio = metabase.MetabaseIO(client)
    db_mapping = {d1: d2 for (d1,d2) in map(lambda x: x.split(":"), db_map)}
    if json_file:
        with open(json_file, 'r') as f:
            source = json.loads(f.read())
    elif yaml_dir:
        splitter = metabase.Splitter(yaml_dir)
        source = splitter.load()
    else:
        raise click.Abort("You need to specify json file with -j or yaml directory with -y")

    if validate:
        if verbose:
            click.echo("🔍 Validating import file coherence...")
        broken_cards = metabase.broken_cards(source['items'], source['datamodel'])
        if len(broken_cards) > 0:
            print("There are broken cards:")
            for bc in broken_cards:
                print("{}: {}".format(*bc))

        broken_dashboards = metabase.broken_dashboards(source['items'])
        if len(broken_dashboards) > 0:
            print("There are broken dashboards (with questions outside of imported collection):")
            for bd in broken_dashboards:
                print("{}: {} (missing card id {})".format(*bd))

        broken_datamodel = metabase.broken_datamodel(source['datamodel'])
        if len(broken_datamodel) > 0:
            print("This is broken in the data model:")
            for bd in broken_datamodel:
                print("{}: {} - {}".format(*bd))

        if len(broken_cards) > 0 or len(broken_dashboards) > 0 or len(broken_datamodel) > 0:
            return 1


    mio.import_json(source, collection, metadata,
                    overwrite,
                    db_mapping)


@cli.command(aliases=['t'])
@click.option('--no-fixtures', is_flag=True, help="Do not load configured fixtures before running the test suite")
@click.argument('test_config', default='keanu-test.yaml', type=click.Path(exists=True))
@click.argument('test_dir', default='tests', type=click.Path(exists=True))
@click.argument('spec',  required=False)
def test(test_config, test_dir, spec, no_fixtures):
    """
    Run tests from TEST_DIR (default tests), using batch configuration from TEST_CONFIG (default keanu-test.yaml).
    You should configure the batch in test file in a way that is similar to your production setup. Each test will make a full load of loaders defined by script ORDER variable, similar to load -o option format.

    Use spec to limit test files, it defaults to test*.py when omitted.
    """
    configuration = config.configuration_from_argument(test_config)
    suite = TestLoaders(configuration, no_fixtures)
    result = suite.run(test_dir, spec)

    # if result.wasSuccessful():
    #     click.echo("All {} tests pass".format(result.testsRun))
    #     return 0

    # for (t, tb) in result.errors:
    #     click.echo("💔  Error in {}\n{}".format(t,tb))

    # for (t, tb) in result.failures:
    #     click.echo("😞  Failure in {}\n{}".format(t, tb))

    # click.echo("{} tests failed".format(len(result.failures)))
    # sys.exit(1)

@metabase_cli.command('query', aliases=['q'])
@click.option('-j', '--json', is_flag=True, default=False, help="Print in JSON instead of Python")
@click.argument('model')
@click.argument('oid', default=None, required=False)
@click.argument('sub', default=None, required=False)
def metabase_query(model, oid, sub, **opts):
    from pprint import pprint
    client = metabase.Client()

    r = client.get(model, oid, sub)

    if opts['json']:
        print(json.dumps(r, indent=2))
    else:
        pprint(r)

@metabase_cli.command('split', aliases=['s'])
@click.option('-j', '--json-file', help="path to JSON file to import")
@click.option('-y', '--yaml-dir', help="path to directory with yaml files")
def metabase_split(json_file, yaml_dir):
    data = json.load(open(json_file))
    splitter = metabase.Splitter(yaml_dir)
    splitter.store(data)

@metabase_cli.command('join', aliases=['j'])
@click.option('-j', '--json-file', default=None, help="path to JSON file to import")
@click.option('-y', '--yaml-dir', help="path to directory with yaml files")
def metabase_split(json_file, yaml_dir):
    splitter = metabase.Splitter(yaml_dir)
    data = splitter.load()
    if json_file:
        with open(json_file, 'w') as out:
            out.write(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(json.dumps(data, indent=2, sort_keys=True))

def set_verbose(verbose):
    if verbose:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('metabase.io').setLevel(logging.INFO)
