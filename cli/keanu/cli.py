from dotenv import load_dotenv
load_dotenv()

import click
import json
from glob import glob
from os import environ
from . import db, util, metabase, config
from .sql_loader import SqlLoader
from .db_destination import DBDestination
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
import re
import sys
import traceback
import logging


@click.group()
def cli():
    pass

def positive_int(ctx, param, value):
    v = int(value)
    if v >= 1:
        return v
    else:
        raise click.BadParameter("-t thread_number must be a positive integer")

@cli.command()
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




@cli.command()
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



@cli.command()
@click.option('-D', '--drop', is_flag=True, default=False, help='DROP TABLEs before running the script')
@click.option('-L', '--load', default=None, help='Load this SQL file')
@click.argument('database_url')
def schema(drop, load, database_url):
    dest = DBDestination({'url': environ['DATABASE_URL']})
    connection = dest.connection()

    if drop:
        for (table, _) in connection.execute("show full tables where Table_Type = 'BASE TABLE'"):
            connection.execute('SET FOREIGN_KEY_CHECKS = 0')
            click.echo('💥 Dropping table {}'.format(table))
            connection.execute('DROP TABLE {}'.format(table))

    if load:
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


@cli.group('metabase')
def metabase_cli():
  pass

@metabase_cli.command('export')
@click.option('-c', '--collection', help="Name of the collection to export")
def metabase_export(collection):
    client = metabase.Client()
    mio = metabase.MetabaseIO(client)
    result = mio.export_json(collection)
    print(json.dumps(result, indent=2))

@metabase_cli.command('import')
@click.option('-c', '--collection', help="Name of the collection to import into")
@click.option('-j', '--json-file', help="path to JSON file to import")
@click.option('-m', '--metadata', is_flag=True, help="Also import metadata before importing the collection")
def metabase_import(collection, json_file, metadata):
    client = metabase.Client()
    mio = metabase.MetabaseIO(client)
    with open(json_file, 'r') as f:
        source = json.loads(f.read())
        mio.import_json(source, collection, metadata)


def set_verbose(verbose):
    if verbose:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
