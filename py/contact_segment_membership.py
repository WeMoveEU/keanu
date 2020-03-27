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
from civicrm import group_history, group_history_max_id, sql_for_contacts_who_changed

ORDER = 60

# Calculate membership
# Member -> civicrm group subscription on Mamber
# Expiring -> from then 1 year
# Expired ->
#
#
#
# update will check existing rows


BATCH_SIZE = 1000000

def delete(_):
    dst = _.destination.connection()
    dst.execute("""
DELETE cs
    FROM contact_segment cs
    JOIN segment s ON cs.segment_id = s.id
    JOIN segmentation sn ON sn.id = s.segmentation_id
    WHERE sn.name = 'Membership'
    """)

# named tuple resembling hte contact_segment table row
# its a tuple but with attribute access, makes code more readable.
ContactSegment = collections.namedtuple(
    "ContactSegment",
    ['segmentation_id', 'segment_id', 'contact_id', 'joined_at', 'left_at'])

Segment = collections.namedtuple(
    "Segment",
    ["segmentation_id", "segment_id"])



def execute(_):
    src = _.source.connection()
    dst = _.destination.connection()
    meta = MetaData(dst)
    table = Table("contact_segment", meta, autoload=True)

    member_segment_id, member_group_id, membership_sn_id = dst.execute("SELECT id, external_id, segmentation_id FROM segment WHERE name = 'Member'").fetchone()
    expiring_segment_id = dst.execute("SELECT id FROM segment WHERE name = 'Expiring'").fetchone()[0]
    expired_segment_id = dst.execute("SELECT id FROM segment WHERE name = 'Expired'").fetchone()[0]

    max_contact_id = dst.execute("SELECT max(id) FROM contact").fetchone()[0]

    # batch until max_contact_id
    # get history for group in question
    # group by contact_id
    # for each contact_id, story
    # calculate tuples for join leave
    # join them and put into DT

    def full_load(thread):
        src = _.source.connection()
        dst = _.destination.connection()

        batches = ranges(range(0, max_contact_id + 1, BATCH_SIZE), last=(max_contact_id+1))
        for contact_range in _.slice_for_thread(batches, thread):

            acc = []

            hist = group_history(_, src, member_group_id, contact_range=contact_range)

            cont = contacts(src, contact_range=contact_range)

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

            all_cs = list(map(lambda r: r._asdict(), itertools.chain(*acc)))
            dst.execute(table.insert(), all_cs)


    # FULL
    if _.options['incremental'] == False:
        _.threaded(full_load)
    
        last_sync.save_last_sync_id(dst, 'contact_segment', 'civicrm_subscription_history.member', max_contact_id)

    else:
    # INCREMENTAL
        next_to_sync_history_id = lasts.sync_last_sync_id(
            dst, 'contact_segment', 'civicrm_subscription_history.member') + 1

        contacts_which_changed = sql_for_contacts_who_changed(_, member_group_id,
                                                             next_to_sync_history_id)

        hist = group_history(_, src, member_group_id, contact_select=contacts_which_changed)


        



def group_history_to_segments(events, contact_id, segment):
    """
events - list of subscription events from CiviCRM, returned by group_history(...)
contact_id
segment - the segment this gorup maps to
    """
    cs = []

    NON_MEMBER = 0
    MEMBER = 1
    state = NON_MEMBER
    last_join = None

    for e in events:

        if state == NON_MEMBER and e["is_join"]:
            state = MEMBER
            last_join = e["date"]
        elif state == MEMBER and not e["is_join"]:
            state = NON_MEMBER
            cs.append(ContactSegment(segment.segmentation_id, segment.segment_id, contact_id, last_join, e["date"]))
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
