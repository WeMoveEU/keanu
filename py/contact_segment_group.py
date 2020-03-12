import click
from contact_segment_membership import group_history, group_history_to_segments
from sqlalchemy import text, bindparam
import pandas as pd
import itertools

ORDER = 69
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

    group_segments = non_member_group_segments(dst)

    group_id_to_segment_id = { eid: sid for (sid, eid, snid) in group_segments}
    segment_id_to_segmentation_id = { sid: snid for (sid, eid, snid) in group_segments}
    group_ids = [eid for (sid, eid, snid) in group_segments]

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    for start in range(0, max_contact_id + 1, BATCH_SIZE):
        click.echo("\033[2K\r🚀 range {}/{}\b".format(start, max_contact_id), nl=False)
        contact_range = (start, start + BATCH_SIZE)
    
        acc = []

        hist = group_history(_, src, contact_range, group_ids)

        for (group_id, contact_id), event_idx in \
            hist.groupby(['group_id', 'contact_id']).groups.items():

            events = hist.iloc[event_idx]
            segment_id = group_id_to_segment_id[group_id]
            cs = group_history_to_segments(events, contact_id, segment_id)
            acc.append(cs)

        all_cs = pd.DataFrame(itertools.chain(*acc),
                              columns=["segment_id", "contact_id", "joined_at", "left_at"])

        segmentation_ids = all_cs.apply(
            lambda row: segment_id_to_segmentation_id[row["segment_id"]],
            axis=1
        )

        all_cs['segmentation_id'] = segmentation_ids

        all_cs.to_sql("contact_segment", dst, index=False, if_exists='append')


