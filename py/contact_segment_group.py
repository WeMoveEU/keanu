import click
from contact_segment_membership import \
    group_history, group_history_to_segments, ContactSegment, Segment
from sqlalchemy import text, bindparam
from sqlalchemy.schema import Table, MetaData
import pandas as pd
import itertools

ORDER = 61
BATCH_SIZE = 100000

def non_member_group_segments(conn):
    return conn.execute("""
SELECT id, external_id, segmentation_id
    FROM segment
    WHERE external_system = 'civicrm_group' AND name != 'Member'
    """).fetchall()


def delete(_):
    src = _.source.connection()
    dst = _.destination.connection()

    group_segments = non_member_group_segments(dst)

    sql = """
    DELETE FROM contact_segment where segment_id IN :ids
    """

    return dst.execute(text(sql).bindparams(bindparam('ids', expanding=True)),
                ids=list(map(lambda gs: gs[0], group_segments)))
    


def execute(_):
    src = _.source.connection()
    dst = _.destination.connection()
    meta = MetaData(dst)
    table = Table("contact_segment", meta, autoload=True)

    group_segments = non_member_group_segments(dst)

    group_id_to_segment = { exid: Segment(snid, sid)  for (sid, exid, snid) in group_segments }
    group_ids = [eid for (sid, eid, snid) in group_segments]

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    for start in range(0, max_contact_id + 1, BATCH_SIZE):
        click.echo("\033[2K\r🚀 range {}/{}\b".format(start, max_contact_id), nl=False)
        contact_range = (start, start + BATCH_SIZE)
    
        acc = []

        hist = group_history(_, src, contact_range, group_ids)

        for (group_id, contact_id), events in itertools.groupby(hist, lambda r: (r['group_id'], r['contact_id'])):
            segment = group_id_to_segment[group_id]
            cs = group_history_to_segments(events, contact_id, segment)
            acc.append(cs)


        all_cs = list(map(lambda r: r._asdict(), itertools.chain(*acc)))
        dst.execute(table.insert(), all_cs)


def execute_parallel(_, thread):
    src = _.source.connection()
    dst = _.destination.connection()
    meta = MetaData(dst)
    table = Table("contact_segment", meta, autoload=True)

    group_segments = non_member_group_segments(dst)

    group_id_to_segment = { exid: Segment(snid, sid)  for (sid, exid, snid) in group_segments }
    group_ids = [eid for (sid, eid, snid) in group_segments]

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    batches = range(0, max_contact_id + 1, BATCH_SIZE)
    for start in _.batch_for_thread(batches, thread):
        contact_range = (start, start + BATCH_SIZE)
    
        acc = []

        hist = group_history(_, src, contact_range, group_ids)

        for (group_id, contact_id), events in itertools.groupby(hist, lambda r: (r['group_id'], r['contact_id'])):
            segment = group_id_to_segment[group_id]
            cs = group_history_to_segments(events, contact_id, segment)
            acc.append(cs)


        all_cs = list(map(lambda r: r._asdict(), itertools.chain(*acc)))
        dst.execute(table.insert(), all_cs)



