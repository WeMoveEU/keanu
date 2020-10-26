import warnings
from signal import SIGTERM, signal
from time import time

from click import echo, exceptions
from sqlalchemy import text


class RunStatement:
    def execute(self, connection, statements, warn=False):
        (connection_id,) = connection.execute("SELECT connection_id()").fetchone()
        result = None
        with warnings.catch_warnings():
            if not warn:
                warnings.simplefilter("ignore", category=Warning)
            try:
                for sql in statements:
                    sql = sql.replace(":", "\\:")
                    yield "sql.statement.start", {"sql": sql, "script": self}
                    start_time = time()
                    result = connection.execute(text(sql))
                    yield "sql.statement.end", {
                        "sql": sql,
                        "script": self,
                        "time": time() - start_time,
                        "result": result,
                    }
            except (KeyboardInterrupt, exceptions.Abort) as ki:
                echo("🔫 Killing sql process {0} 🔫".format(connection_id))
                kill_conn = connection.engine.connect()
                kill_conn.execute("KILL {0}".format(connection_id))
                raise ki


def stopped(_a, _b):
    raise exceptions.Abort("Stopped")


signal(SIGTERM, stopped)
