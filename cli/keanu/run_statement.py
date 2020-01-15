import warnings
from sqlalchemy import text
from .db import get_engine
import click
from time import time


class RunStatement:
    def execute(_, connection, statements, warn=False):
        connection_id, = connection.execute('SELECT connection_id()').fetchone()
        result = None
        with warnings.catch_warnings():
            if not warn:
                warnings.simplefilter("ignore", category=Warning)
            try:
                for sql in statements:
                    yield 'sql.statement.start', {'sql': sql, 'script': _ }
                    start_time = time()
                    result = connection.execute(text(sql))
                    yield 'sql.statement.end', { 'sql': sql, 'script': _,
                                                 'time': time() - start_time, 'result': result }
            except KeyboardInterrupt as ki:
                click.echo("🔫 Killing sql process {0} 🔫".format(connection_id))
                kill_conn = connection.engine.connect()
                kill_conn.execute('KILL {0}'.format(connection_id))
                raise ki
