from sqlalchemy import text

IGNORE = True

def last_sync_id(conn, dst, src):
    last_id = conn.execute(
        text("""
        SELECT last_id FROM last_sync
        WHERE dst = :dst AND src = :src
        """),
        dst=dst, src=src).fetchone()[0]

    return last_id


def save_last_sync_id(conn, destination, source, last_id):
    sql = """
    INSERT INTO last_sync (dst, src, last_id) VALUES (:dst, :src, :last_id)
    ON DUPLICATE KEY UPDATE last_id = :last_id
    """

    conn.execute(text(sql), dst=destination, src=source, last_id=last_id)
    return last_id

