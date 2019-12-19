from dotenv import load_dotenv
load_dotenv()

import click
import json
from glob import glob
from . import db, util, metabase
from .load_script import LoadScript
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
import re
import sys
import traceback

@click.group()
def cli():
    pass

@cli.command()
@click.option('-i', '--incremental', is_flag=True, default=False, help='incremental load')
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default='0:', help='specify order of files to run by (eg. 10 or 10,12 or 10:15,60 etc)')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
def load(incremental, order, dry_run, display, warn):
    opts = { 'incremental': incremental, 'display': display, 'warn': warn }
    scripts = util.get_scripts(opts)

    scripts = util.filter_scripts_by_order(scripts, order)

    try:
        if not dry_run:
            connection = db.get_engine().connect()
        for scr in scripts:
            click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                scr.order,
                scr.filename[len(util.SQLBASE):] if scr.filename.startswith(util.SQLBASE) else scr.filename,
                len(scr.lines),
                len(scr.statements)))

            if len(scr.statements) == 0:
                continue

            if not dry_run:
                with connection.begin() as transaction:
                    try:
                        res = scr.execute(connection)
                    except KeyboardInterrupt as ctrlc:
                        transaction.rollback()
                        sys.exit(1)
                    except (ProgrammingError, IntegrityError, MySQLError, InternalError, DataError) as e:
                        transaction.rollback()
                        msg = str(e.args[0])
                        msg = msg.replace('\\n', "\n")
                        click.echo(message=msg, err=True)
                        sys.exit(1)
            elif display:
                # it's a dry run and display was requested. Print the script
                for s in scr.statements:
                    click.echo(util.highlight_sql(s))

    except SystemExit as e:
        # rethrow it so it does not fall into unexpected block below:
        raise e

    except:
        t, v, tb = sys.exc_info()
        print("Unexpected error: {0}: {1}", t, v)
        traceback.print_tb(tb, limit=10)

@cli.command()
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default='0:', help='specify order of files to run by (eg. 10 or 10,12 or 10:15,60 etc)')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
def delete(order, display, dry_run, warn):
    opts = { 'display': display, 'warn': warn }
    scripts = util.get_scripts(opts)

    scripts = util.filter_scripts_by_order(scripts, order)

    scripts.reverse()

    connection = db.get_engine().connect()

    for scr in scripts:
        with connection.begin() as transaction:
            click.echo("🚒️ [{:3d}] {} ({})".format(
                scr.order,
                scr.filename,
                ', '.join(map(lambda s: s.rstrip(), map(util.highlight_sql, scr.deleteSql)))),
                       color=True)
            if not dry_run:
                try:
                    scr.delete(connection)
                except KeyboardInterrupt as ctrlc:
                    transaction.rollback()
                    raise ctrlc

@cli.command()
@click.option('-D', '--drop', is_flag=True, default=False, help='DROP TABLEs before running the script')
@click.option('-L', '--load', default=None, help='Load this SQL file')
def schema(drop, load):
    connection = db.get_engine().connect()

    if drop:
        for (table, _) in connection.execute("show full tables where Table_Type = 'BASE TABLE'"):
            connection.execute('SET FOREIGN_KEY_CHECKS = 0')
            click.echo('💥 Dropping table {}'.format(table))
            connection.execute('DROP TABLE {}'.format(table))

    if load:
        script = LoadScript(load)
        script.replace_sql_object('keanu', db.schema_name)
        click.echo("🚚 Loading {}...".format(script.filename))
        with connection.begin() as tx:
            script.execute(connection)


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
def metabase_import(collection, json_file):
    client = metabase.Client()
    mio = metabase.MetabaseIO(client)
    with open(json_file, 'r') as f:
        source = json.loads(f.read())
        mio.import_json(source, collection)


