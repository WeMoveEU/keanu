import os
import pandas as pd
import click
import collections
import itertools
# >>> list(itertools.chain(l1, l2, l3))
from sqlalchemy import text, bindparam
from time import time

# import ipdb

ORDER = 70

# Calculate membership
# Member -> civicrm group subscription on Mamber
# Expiring -> from then 1 year
# Expired ->
#
#
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

    for start in range(0, max_contact_id + 1, BATCH_SIZE):
        contact_range = (start, start + BATCH_SIZE)
        click.echo("\033[2K\r🚀 range {}/{}\b".format(start, max_contact_id), nl=False)
        acc = []

        hist = group_history(_, src, contact_range, member_group_id)

        cont = contacts(src, contact_range)

        for contact_id, event_idx in hist.groupby("contact_id").groups.items():
            events = hist.iloc[event_idx]
            mem_segment = group_history_to_segments(events, contact_id, member_segment_id)

            exp_segments = add_expiring_segments(mem_segment,
                                                 contact_id,
                                                 cont.loc[contact_id,"created_at"],
                                                 expiring_segment_id, expired_segment_id)

            acc.append(mem_segment)
            acc.append(exp_segments)
        
        all_cs = pd.DataFrame(itertools.chain(*acc), columns=["segment_id", "contact_id", "joined_at", "left_at"])
        all_cs.insert(0, "segmentation_id", membership_sn_id)

        all_cs.to_sql("contact_segment", dst, index=False, if_exists='append')
    click.echo("\r🐰 Done.")

def group_history_to_segments(events, contact_id, segment_id):
    cs = []

    ct = len(events)
    NON_MEMBER = 0
    MEMBER = 1
    state = NON_MEMBER
    last_join = None

    for i in range(0, ct):
        e = events.iloc[i]

        if state == NON_MEMBER and e["is_join"]:
            state = MEMBER
            last_join = e["date"]
        elif state == MEMBER and not e["is_join"]:
            state = NON_MEMBER
            cs.append((segment_id, contact_id, last_join, e["date"]))

    if state == MEMBER:
        cs.append((segment_id, contact_id, last_join, None))
    return cs

def fill_interval(from_time, to_time, expiration, contact_id, seg1_id, seg2_id):
    acc = []
    now = pd.Timestamp.now()
    would_expire = from_time + expiration

    if would_expire < (to_time or now):
        acc.append((seg1_id, contact_id, from_time, would_expire))
        acc.append((seg2_id, contact_id, would_expire, to_time)) # to_time can be nil
    else:
        acc.append((seg1_id, contact_id, from_time, to_time)) # to_time can be nil
    return acc

EXPIRATION = pd.Timedelta('1Y')

def add_expiring_segments(member_segments, contact_id, created_at, expiring_seg_id, expired_seg_id):
    now = pd.Timestamp.now()
    cs = []

    # when a contact is created, they are expiring
    # if they did not become members at the same time

    if len(member_segments) > 0:
        # this was a member at least once
        mem_at = member_segments[0][2]

        if mem_at > created_at:
            cs += fill_interval(created_at, mem_at, EXPIRATION, contact_id, expiring_seg_id, expired_seg_id)
        else:
            pass # There is no expiring period before being a member

        # now, after each member period
        for i in range(0, len(member_segments)):
            mem_from = member_segments[i][3]

            if mem_from is None:  # this membership still continues
                break

            mem_to = i + 1 < len(member_segments) and member_segments[i+1][2] or None
            cs += fill_interval(mem_from, mem_to, EXPIRATION, contact_id, expiring_seg_id, expired_seg_id)
    else:
        cs += fill_interval(created_at, None, EXPIRATION, contact_id, expiring_seg_id, expired_seg_id)

    return cs


def contacts(conn, contact_id_range):
    sql = """
    SELECT * FROM contact WHERE id >= :contact_min AND id < :contact_max
    """
    return pd.read_sql(text(sql), conn,
                       index_col="id",
                       params={ "contact_min": contact_id_range[0],
                                "contact_max": contact_id_range[1] })


def group_history(_, conn, contact_range, group_id):
    sql = """
    SELECT
      group_id,
      contact_id,
      date,
      CASE WHEN status = 'Added' THEN true
                                 ELSE false
      END as is_join
    FROM {subscription_history}
          WHERE group_id IN :gid
                AND status IN ('Added', 'Removed')
                AND contact_id >= :contact_min
                AND contact_id < :contact_max
    ORDER by group_id, contact_id, date
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history')
    )

    return pd.read_sql(text(sql).bindparams(bindparam('gid', expanding=True)),
                       conn, params={
                           'gid': isinstance(group_id, int)
                           and [group_id]
                           or list(map(str, group_id)),
                           'contact_min': contact_range[0], 'contact_max': contact_range[1]
                       })


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
