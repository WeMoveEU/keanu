#!/usr/bin/env python
import click
from glob import glob
from keanu import LoadScript, db
from pymysql.err import MySQLError
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError, DataError
import sys
import traceback

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
    files = glob('../sql/**/*.sql', recursive=True)
    scripts = list(map(lambda fn: LoadScript(fn, **opts), files))
    LoadScript.sort(scripts)
    try:
        connection = db.engine.connect()
        for scr in scripts:
            # skip to order
            if scr.order < o: continue

            click.echo("{1}: {0} ({2} lines, {3} statements)".format(
                scr.filename, scr.order, len(scr.lines), len(scr.statements)))

            if n:  # dry run, skip
                continue
            if len(scr.statements) == 0:
                continue

            with connection.begin() as transaction:
                try:
                    res = scr.execute(connection)
                except KeyboardInterrupt as ctrlc:
                    transaction.rollback()
                    raise ctrlc
            click.echo(scr.statement_abbrev(scr.statements[-1]) + ' ROWS: {0}'.format(res.rowcount))

            # stop after one.
            if s:
                break

    except (ProgrammingError, IntegrityError, MySQLError, InternalError, DataError) as e:
        msg = str(e.args[0])
        msg = msg.replace('\\n', "\n")
        click.echo(message=msg, err=True)
        sys.exit(-1)

    except:
        t, v, tb = sys.exc_info()
        print("Unexpected error: {0}: {1}", t, v)
        traceback.print_tb(tb, limit=10)

if __name__ == '__main__':
    cli()
