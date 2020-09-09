import os
import click
import collections
import itertools
import last_sync
from util import ranges, nest_sql
# >>> list(itertools.chain(l1, l2, l3))
from sqlalchemy import text, bindparam
from sqlalchemy.schema import Table, MetaData
from datetime import datetime, timedelta
from civicrm import group_history, group_history_max_id, sql_for_contacts_who_changed_group
from segment import ContactSegment, Segment, update_segments


ORDER = 40

# Calculate membership
# Member -> civicrm group subscription on Member
# Expiring -> from leaving member group until 1 year later or joining again
# Expired -> after 1 year of expiring
#
# update will check existing rows


BATCH_SIZE = 100000

def delete(_):
    dst = _.destination.connection()
    dst.execute("""
DELETE cs
    FROM contact_segment cs
    JOIN segment s ON cs.segment_id = s.id
    JOIN segmentation sn ON sn.id = s.segmentation_id
    WHERE sn.name = 'Membership'
    """)



def execute(_):
    src = _.source.connection()
    dst = _.destination.connection()
    meta = MetaData(dst)
    table = Table("contact_segment", meta, autoload=True)
    query_start = dst.execute("SELECT NOW()").fetchone()[0]

    # Get all revelant segment and group ids
    member_segment_id, member_group_id, membership_sn_id = dst.execute("SELECT id, external_id, segmentation_id FROM segment WHERE name = 'Member'").fetchone()
    expiring_segment_id = dst.execute("SELECT id FROM segment WHERE name = 'Expiring'").fetchone()[0]
    expired_segment_id = dst.execute("SELECT id FROM segment WHERE name = 'Expired'").fetchone()[0]

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    hist_max_id = group_history_max_id(_, member_group_id)

    # given the member group join/leave history from civicrm, and cont-act info (needed to have created_at date)
    # generate contact segments for membership segmentation
    def history_to_segments(hist, cont):
        acc = []
        processed = set()
        for contact_id, events in itertools.groupby(hist, lambda r: r["contact_id"]):
            mem_segment = group_history_to_segments(list(events), contact_id,
                                                    Segment(membership_sn_id, member_segment_id))

            exp_segments = add_expiring_segments(mem_segment,
                                                 contact_id,
                                                 cont[contact_id]["created_at"],
                                                 Segment(membership_sn_id, expiring_segment_id),
                                                 Segment(membership_sn_id, expired_segment_id))

            acc.append(mem_segment)
            acc.append(exp_segments)
            processed.add(contact_id)

        # Take care of all contacts who never became member: they don't appear in history
        unprocessed = cont.keys() - processed
        for contact_id in unprocessed:
            exp_segments = add_expiring_segments([],
                                                 contact_id,
                                                 cont[contact_id]["created_at"],
                                                 Segment(membership_sn_id, expiring_segment_id),
                                                 Segment(membership_sn_id, expired_segment_id))
            acc.append(exp_segments)

        return itertools.chain(*acc)

    # Full load algorithm (to be run in thread)
    def full_load(thread):
        src = _.source.connection()
        dst = _.destination.connection()

        batches = ranges(range(0, max_contact_id + 1, BATCH_SIZE), last=(max_contact_id+1))
        for contact_range in _.slice_for_thread(batches, thread):


            hist = group_history(_, member_group_id, hist_max_id, contact_range=contact_range)

            cont = contacts(src, contact_range=contact_range)

            all_cs = history_to_segments(hist, cont)
            all_cs = map(lambda r: r._asdict(), all_cs)
            all_cs = list(all_cs)
            if all_cs != []:
                dst.execute(table.insert(), all_cs)


    # FULL LOAD 
    if _.options['incremental'] == False:
        _.threaded(full_load)
    
        last_sync.save_last_sync_id(dst, 'contact_segment', 'civicrm_subscription_history.member', hist_max_id)

    else:
    # INCREMENTAL LOAD
        next_to_sync_history_id = last_sync.last_sync_id(
            dst, 'contact_segment', 'civicrm_subscription_history.member') + 1

        contacts_which_changed = sql_for_contacts_who_changed_group(_, member_group_id,
                                                              next_to_sync_history_id,
                                                              hist_max_id)

        hist = group_history(_, member_group_id, hist_max_id, contact_select=contacts_which_changed)
        if hist.rowcount > 0:
            cont = contacts(src, contact_select=contacts_which_changed)
            cs = history_to_segments(hist, cont)
            
            update_segments(dst, cs, list(cont.keys()),
                            [member_segment_id, expiring_segment_id, expired_segment_id])

        last_sync.save_last_sync_id(dst, 'contact_segment', 'civicrm_subscription_history.member', hist_max_id)

    last_sync.save_last_sync_dt(dst, 'contact_segment_membership', 'query_start', query_start)


def group_history_to_segments(events, contact_id, segment):
    """
events - list of subscription events from CiviCRM, returned by group_history(...)
contact_id
segment - the segment this group maps to
    """
    cs = []

    NON_MEMBER = 0
    MEMBER = 1
    state = NON_MEMBER
    last_join = None
    minimal_join_time = timedelta(seconds=1)

    for e in events:

        if state == NON_MEMBER and e["is_join"]:
            state = MEMBER
            last_join = e["date"]
        elif state == MEMBER and not e["is_join"]:
            state = NON_MEMBER
            if last_join < e["date"]:
                leave_at = e["date"]
            else:
                leave_at = last_join + minimal_join_time
            cs.append(ContactSegment(segment.segmentation_id, segment.segment_id, contact_id, last_join, leave_at))
        elif state == MEMBER and e["is_join"]:
            pass
        elif state == NON_MEMBER and not e["is_join"]:
            pass


    if state == MEMBER:
        cs.append(ContactSegment(segment.segmentation_id, segment.segment_id, contact_id, last_join, None))
    return cs

def fill_interval(from_time, to_time, expiration, contact_id, seg1, seg2):
    acc = []
    now = datetime.utcnow()
    would_expire = from_time + expiration

    if would_expire < (to_time or now):
        acc.append(ContactSegment(seg1.segmentation_id, seg1.segment_id, contact_id, from_time, would_expire))
        acc.append(ContactSegment(seg2.segmentation_id, seg2.segment_id, contact_id, would_expire, to_time)) # to_time can be nil
    else:
        acc.append(ContactSegment(seg1.segmentation_id, seg1.segment_id, contact_id, from_time, to_time)) # to_time can be nil
    return acc

EXPIRATION = timedelta(days=365)

def add_expiring_segments(member_segments, contact_id, created_at, expiring_seg, expired_seg):
    now = datetime.utcnow()
    cs = []

    # when a contact is created, they are expiring
    # if they did not become members at the same time

    try:
        # this was a member at least once
        mem_at = member_segments[0].joined_at

        if mem_at > created_at:
            cs += fill_interval(created_at, mem_at, EXPIRATION, contact_id, expiring_seg, expired_seg)
        else:
            pass # There is no expiring period before being a member

        # now, after each member period
        for i, member_segment in enumerate(member_segments):
            mem_from = member_segment.left_at

            if mem_from is None:  # this membership still continues
                break

            try:
                mem_to = member_segments[i+1].joined_at
            except IndexError:
                mem_to = None
            cs += fill_interval(mem_from, mem_to, EXPIRATION, contact_id, expiring_seg, expired_seg)
    except IndexError:
        cs += fill_interval(created_at, None, EXPIRATION, contact_id, expiring_seg, expired_seg)

    return cs


def contacts(conn, contact_range=None, contact_select=None):
    if contact_range is not None:
        sql = text("""
        SELECT * FROM contact WHERE
        id >= :min AND id < :max
        """).bindparams(min=contact_range[0], max=contact_range[1])

    elif contact_select is not None:
        sql = """
        SELECT * FROM contact WHERE
        contact.id IN ({contact_select})
        """
        sql = nest_sql(sql, contact_select=contact_select)

    return {
        row[0]: row
        for
        row in conn.execute(sql)
    }


def prop_loader():
    from keanu import config
    batch = config.build_batch({}, config.configuration_from_argument("."))
    script = collections.namedtuple('Script', ['source', 'destination'])
    l = script(batch.sources[0], batch.destination)
    return l

def main():
    l = prop_loader()
    return execute(l)

if __name__ == '__main__':
    main()
