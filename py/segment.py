from sqlalchemy import text, bindparam
from sqlalchemy.schema import Table, MetaData
from util import get_table
import itertools
import collections

IGNORE=True

# named tuple resembling hte contact_segment table row
# its a tuple but with attribute access, makes code more readable.
ContactSegment = collections.namedtuple(
    "ContactSegment",
    ['segmentation_id', 'segment_id', 'contact_id', 'joined_at', 'left_at'])

Segment = collections.namedtuple(
    "Segment",
    ["segmentation_id", "segment_id"])


def update_segments(conn, cs_list, contacts, segments):
    cs_table = get_table(conn, 'contact_segment')

    existing_cs_sql = """
    SELECT
    id, segmentation_id, segment_id, contact_id, joined_at, left_at
    FROM contact_segment
    WHERE
    contact_id IN :contacts AND
    segment_id IN :segments
    ORDER BY 1, 2, 3, 4
    """

    existing_cs_sql = text(existing_cs_sql).bindparams(contacts=contacts,
                                                       segments=segments)

    res = conn.execute(existing_cs_sql)
    existing = {(r["segment_id"], r["contact_id"], r["joined_at"]):  r for r in res.fetchall()}

    to_insert = []
    to_update = []
    for cs in cs_list:
        try:
            key = (cs.segment_id, cs.contact_id, cs.joined_at)
            excs = existing.pop(key)
            # exists
            if excs['left_at'] != cs.left_at:
                # needs update
                to_update.insert(0, {'left_at': cs.left_at, '_id': excs['id']})
        except KeyError:
            to_insert.insert(0, cs._asdict())

    if len(existing):
        dele = cs_table.delete().where(cs_table.c.id == bindparam('_id'))
        conn.execute(dele, list(map(lambda e: {'_id': e['id']}, existing.values())))

    if len(to_update) > 0:
        upd = cs_table.update().where(cs_table.c.id == bindparam('_id')).\
            values({'left_at': bindparam('left_at')})
        conn.execute(upd, to_update)

    if len(to_insert) > 0:
        conn.execute(cs_table.insert(), to_insert)


def get_segmentation(conn, segmentation_name):
    sql = text("""
    SELECT s.name, s.id, sn.id
    FROM segment s
    JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name = :sn_name
    """)
    sql = sql.bindparams(sn_name=segmentation_name)


    return {name: Segment(snid, sid) 
            for (name, sid, snid)
            in conn.execute(sql).fetchall()}
