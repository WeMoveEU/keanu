#!/usr/bin/env python
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
@click.option('-i', is_flag=True, default=False, help='incremental load')
@click.option('-n', is_flag=True, default=False, help='dry run')
@click.option('-o', default=0, help='start from order number')
@click.option('-s', is_flag=True, default=False, help='run just one SQL')
@click.option('-d', is_flag=True, default=False, help='display SQL')
def load(i=False, o=0, n=False, s=False, d=False):
    opts = { 'incremental': i, 'display': d }
    scripts = get_scripts(opts)
    try:
        connection = db.engine.connect()
        for scr in scripts:
            # skip to order number if requested
            if scr.order < o: continue

            click.echo("🚚 [{:3d}] {} ({} lines, {} statements)".format(
                scr.order,
                scr.filename[len(SQLBASE):] if scr.filename.startswith(SQLBASE) else scr.filename,
                len(scr.lines),
                len(scr.statements)))

            if n:  # dry run, skip
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
            if s:
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
@click.option('-n', is_flag=True, default=False, help='dry run')
@click.option('-o', default=0, help='go back until order number')
@click.option('-s', is_flag=True, default=False, help='run just one SQL')
@click.option('-d', is_flag=True, default=False, help='display SQL')
def delete(o=0, d=False, n=False, s=False):
    opts = { 'display': d }
    scripts = get_scripts(opts)
    scripts.reverse()

    connection = db.engine.connect()

    if s:
        scripts = filter(lambda a: a.order == o, scripts)

    for scr in scripts:
        if scr.order < o:
            break
        with connection.begin() as transaction:
            click.echo("🚒️ [{:3d}] {} ({})".format(
                scr.order,
                scr.filename,
                ', '.join(map(lambda s: s.rstrip(), map(util.highlight_sql, scr.deleteSql)))),
                       color=True)
            if not n:
                try:
                    scr.delete(connection)
                except KeyboardInterrupt as ctrlc:
                    transaction.rollback()
                    raise ctrlc


# helpers

def get_scripts(opts={}):
    files = glob(SQLBASE+'**/*.sql', recursive=True)
    scripts = list(map(lambda fn: LoadScript(fn, **opts), files))
    LoadScript.sort(scripts)
    return scripts


if __name__ == '__main__':
    cli()
