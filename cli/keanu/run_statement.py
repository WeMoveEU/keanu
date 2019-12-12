import warnings
from sqlalchemy import text
from .db import get_engine
import click
from time import time


class RunStatement:
    def execute(_, connection, statements, display=False, warn=False):
        connection_id, = connection.execute('SELECT connection_id()').fetchone()
        result = None
        with warnings.catch_warnings():
            if not warn:
                warnings.simplefilter("ignore", category=Warning)
            try:
                for sql in statements:
                    yield 'start', {'sql': sql }
                    start_time = time()
                    result = connection.execute(text(sql))
                    yield 'end', { 'sql': sql, 'time': time() - start_time, 'result': result }
            except KeyboardInterrupt as ki:
                click.echo("🔫 Killing sql process {0} 🔫".format(connection_id))
                kill_conn = get_engine().connect()
                kill_conn.execute('KILL {0}'.format(connection_id))
                raise ki
