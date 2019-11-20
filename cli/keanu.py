#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()
import click
from glob import glob
from keanu import LoadScript, db, util
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
import sys
import traceback

SQLBASE='../sql/'

@click.group()
def cli():
    pass

@cli.command()
@click.option('-i', '--incremental', is_flag=True, default=False, help='incremental load')
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default=0, help='start from order number')
@click.option('-s', '--single', is_flag=True, default=False, help='run just one SQL')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
def load(incremental=False, order=0, dry_run=False, single=False, display=False, warn=False):
    opts = { 'incremental': incremental, 'display': display, 'warn': warn }
    scripts = get_scripts(opts)
    try:
        connection = db.engine.connect()
        for scr in scripts:
            # skip to order number if requested
            if scr.order < order: continue

            click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                scr.order,
                scr.filename[len(SQLBASE):] if scr.filename.startswith(SQLBASE) else scr.filename,
                len(scr.lines),
                len(scr.statements)))

            if dry_run:  # dry run, skip
                continue
            if len(scr.statements) == 0:
                continue

            with connection.begin() as transaction:
                try:
                    res = scr.execute(connection)
                except KeyboardInterrupt as ctrlc:
                    transaction.rollback()
                    sys.exit(1)

            # stop after one.
            if single:
                break

    except (ProgrammingError, IntegrityError, MySQLError, InternalError, DataError) as e:
        msg = str(e.args[0])
        msg = msg.replace('\\n', "\n")
        click.echo(message=msg, err=True)
        sys.exit(1)

    except SystemExit as e:
        raise e

    except:
        t, v, tb = sys.exc_info()
        print("Unexpected error: {0}: {1}", t, v)
        traceback.print_tb(tb, limit=10)

@cli.command()
@click.option('-n', '--dry-run', is_flag=True, default=False, help='dry run')
@click.option('-o', '--order', default=0, help='go back until order number')
@click.option('-s', '--single', is_flag=True, default=False, help='run just one SQL')
@click.option('-d', '--display', is_flag=True, default=False, help='display SQL')
@click.option('-W', '--warn', is_flag=True, default=False, help='display SQL warnings')
def delete(order=0, display=False, dry_run=False, single=False, warn=False):
    opts = { 'display': display, 'warn': warn }
    scripts = get_scripts(opts)
    scripts.reverse()

    connection = db.engine.connect()

    if single:
        scripts = filter(lambda a: a.order == order, scripts)

    for scr in scripts:
        if scr.order < order:
            break
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
    connection = db.engine.connect()

    if drop:
        for (table, _) in connection.execute("show full tables where Table_Type = 'BASE TABLE'"):
            connection.execute('SET FOREIGN_KEY_CHECKS = 0')
            click.echo('💥 Dropping table {}'.format(table))
            connection.execute('DROP TABLE {}'.format(table))

    if load:
        script = LoadScript(load)
        click.echo("🚚 Loading {}...".format(script.filename))
        with connection.begin() as tx:
            script.execute(connection)


# helpers

def get_scripts(opts={}):
    files = glob(SQLBASE+'**/*.sql', recursive=True)
    scripts = list(map(lambda fn: LoadScript(fn, **opts), files))
    LoadScript.sort(scripts)
    return scripts


if __name__ == '__main__':
    cli()
