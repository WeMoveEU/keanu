import click
from contact_segment_membership import \
    group_history, group_history_to_segments, ContactSegment, Segment
from sqlalchemy import text, bindparam
from sqlalchemy.schema import Table, MetaData
import pandas as pd
import itertools
import last_sync
from util import ranges, get_table, nest_sql
from civicrm import group_history, group_history_max_id, sql_for_contacts_who_changed_group
from segment import update_segments

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
    table = get_table(dst, 'contact_segment')

    group_segments = non_member_group_segments(dst)

    group_id_to_segment = { exid: Segment(snid, sid)  for (sid, exid, snid) in group_segments }
    group_ids = list(group_id_to_segment.keys())
    segment_ids = list(map(lambda s: s.segment_id, group_id_to_segment.values()))

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]
    hist_max_id = group_history_max_id(_, group_ids)

    if _.options['incremental'] == False:
        hist_max_id = int(hist_max_id /  2)

    def full_load(thread):
        src = _.source.connection()
        dst = _.destination.connection()

        batches = ranges(range(0, max_contact_id + 1, BATCH_SIZE), last=(max_contact_id+1))
        for contact_range in _.slice_for_thread(batches, thread):
            acc = []

            hist = group_history(_,  group_ids, hist_max_id, contact_range=contact_range)

            for (group_id, contact_id), events in itertools.groupby(hist, lambda r: (r['group_id'], r['contact_id'])):
                segment = group_id_to_segment[group_id]
                cs = group_history_to_segments(events, contact_id, segment)
                acc.append(cs)


            all_cs = list(map(lambda r: r._asdict(), itertools.chain(*acc)))
            if len(all_cs):
                dst.execute(table.insert(), all_cs)

        last_sync.save_last_sync_id(dst, 'contact_segment',
                                    'civicrm_subscription_history.group', hist_max_id)

    def incremental_load():
        next_to_sync_history_id = last_sync.last_sync_id(
            dst, 'contact_segment', 'civicrm_subscription_history.group') + 1

        contacts_which_changed = sql_for_contacts_who_changed_group(_, group_ids,
                                                              next_to_sync_history_id,
                                                              hist_max_id)
        hist = group_history(_, group_ids, hist_max_id, contact_select=contacts_which_changed)

        print("history rows {}".format(hist.rowcount))
        if hist.rowcount > 0:
            acc = []
            contacts_seen = set()
            for (group_id, contact_id), events in itertools.groupby(hist, lambda r: (r['group_id'], r['contact_id'])):
                segment = group_id_to_segment[group_id]
                cs = group_history_to_segments(events, contact_id, segment)
                acc.append(cs)
                contacts_seen.add(contact_id)

            acc = itertools.chain(*acc)
            update_segments(dst, acc, list(contacts_seen), segment_ids)

        last_sync.save_last_sync_id(dst, 'contact_segment',
                                    'civicrm_subscription_history.group', hist_max_id)



    if _.options['incremental'] == False:
        _.threaded(full_load)
    else:
        incremental_load()
