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

ORDER = 41
BATCH_SIZE = 100000

def non_member_group_segments(conn):
    """Fetch segment rows for segments that are CiviCRM group based, but not
Member list, because this one is handled by membership loader.
    """
    return conn.execute("""
SELECT id, external_id, segmentation_id
    FROM segment
    WHERE external_system = 'civicrm_group' AND name != 'Member'
    """).fetchall()


def delete(_):
    """Delete contact_segments for segments handled by this loader.
    """
    src = _.source.connection()
    dst = _.destination.connection()

    group_segments = non_member_group_segments(dst)
    segment_ids = list(map(lambda gs: gs[0], group_segments))

    if len(segment_ids) > 0:
        sql = text("""
        DELETE FROM contact_segment where segment_id IN :ids
        """).bindparams(ids=segment_ids)

        return dst.execute(sql)

def execute(_):
    """Run the loader.

    This method does:
    1. Fetch segments with their external_id's - which are CiviCRM group ids
    2. Find out the maximum civicrm group subscription history id and keanu contact id as well as - these will be bounds for current loading.
    3. Run full load (threaded) or incremental
    """
    src = _.source.connection()
    dst = _.destination.connection()
    table = get_table(dst, 'contact_segment')
    query_start = dst.execute("SELECT NOW()").fetchone()[0]

    group_segments = non_member_group_segments(dst)

    group_id_to_segment = { exid: Segment(snid, sid)  for (sid, exid, snid) in group_segments }
    group_ids = list(group_id_to_segment.keys())
    segment_ids = list(map(lambda s: s.segment_id, group_id_to_segment.values()))

    hist_max_id = group_history_max_id(_, group_ids)
    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    def full_load(thread):
        """
        Does the full load:
        1. fetch connections again. If these are new threads, new connections will be made
        2. creates batches of contact id ranges to process, runs (possibly threaded) for every batch
        3. fetch group subscription history for batch of contacts, for specified groups
        4. for each group_id and contact_id, generate contact_segment records
        5. insert all the contact_segment record for a batch
        6. last, save last_sync_id equal to last process subscription history record
        """
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
        """
        Does the incremental load:
        1. Fetch last processed history id, a checkpoint
        2. get subquery SQL for selecting contacts that had some change in groups of interest, since checkpoint
        3. get subscription history for these contacts, using the subquery
        4. for each group_id, contact_id, create contact_segment records
        5. 
        """
        next_to_sync_history_id = last_sync.last_sync_id(
            dst, 'contact_segment', 'civicrm_subscription_history.group') + 1

        contacts_which_changed = sql_for_contacts_who_changed_group(_, group_ids,
                                                              next_to_sync_history_id,
                                                              hist_max_id)
        hist = group_history(_, group_ids, hist_max_id, contact_select=contacts_which_changed)

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

    last_sync.save_last_sync_dt(dst, 'contact_segment_group', 'query_start', query_start)
