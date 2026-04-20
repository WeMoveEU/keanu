from sqlalchemy import text

from ..run_statement import RunStatement


RETENTION_DAYS = 90


def _flavor(conn):
    return RunStatement().flavor(conn)


def _insert_returning_id(conn, sql_mysql, sql_postgres, params):
    flv = _flavor(conn)
    if flv == 'mysql':
        result = conn.execute(text(sql_mysql), **params)
        return result.lastrowid
    elif flv == 'postgresql':
        result = conn.execute(text(sql_postgres + " RETURNING id"), **params)
        return result.fetchone()[0]
    else:
        raise Exception("Unsupported SQL flavor: {}".format(flv))


def start_cycle(conn, batch_name):
    sql_mysql = """
    INSERT INTO loader_cycle (batch_name, started_at, status)
    VALUES (:batch_name, NOW(), 'running')
    """
    sql_postgres = """
    INSERT INTO loader_cycle (batch_name, started_at, status)
    VALUES (:batch_name, NOW(), 'running')
    """
    return _insert_returning_id(
        conn, sql_mysql, sql_postgres, {"batch_name": batch_name}
    )


def end_cycle(conn, cycle_id, status):
    conn.execute(
        text(
            """
            UPDATE loader_cycle
            SET finished_at = NOW(), status = :status
            WHERE id = :cycle_id
            """
        ),
        cycle_id=cycle_id,
        status=status,
    )


def start_run(conn, cycle_id, script_name, script_order):
    sql_mysql = """
    INSERT INTO loader_run (cycle_id, script_name, script_order, started_at, status)
    VALUES (:cycle_id, :script_name, :script_order, NOW(), 'running')
    """
    sql_postgres = sql_mysql
    return _insert_returning_id(
        conn,
        sql_mysql,
        sql_postgres,
        {
            "cycle_id": cycle_id,
            "script_name": script_name,
            "script_order": script_order,
        },
    )


def end_run(conn, run_id, status, error_message=None):
    conn.execute(
        text(
            """
            UPDATE loader_run
            SET finished_at = NOW(), status = :status, error_message = :error_message
            WHERE id = :run_id
            """
        ),
        run_id=run_id,
        status=status,
        error_message=error_message,
    )


def prune(conn):
    """Delete cycles (and their runs) older than RETENTION_DAYS.

    Runs are deleted first to satisfy the FK. Only fully-finished cycles are
    considered, so an in-flight cycle is never removed.
    """
    flv = _flavor(conn)
    if flv == 'mysql':
        cutoff = "NOW() - INTERVAL {} DAY".format(RETENTION_DAYS)
    elif flv == 'postgresql':
        cutoff = "NOW() - INTERVAL '{} days'".format(RETENTION_DAYS)
    else:
        raise Exception("Unsupported SQL flavor: {}".format(flv))

    conn.execute(
        text(
            """
            DELETE FROM loader_run
            WHERE cycle_id IN (
                SELECT id FROM loader_cycle
                WHERE started_at < {cutoff} AND finished_at IS NOT NULL
            )
            """.format(cutoff=cutoff)
        )
    )
    conn.execute(
        text(
            """
            DELETE FROM loader_cycle
            WHERE started_at < {cutoff} AND finished_at IS NOT NULL
            """.format(cutoff=cutoff)
        )
    )
