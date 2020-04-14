from sqlalchemy import text,bindparam
from util import ranges, get_table, nest_sql
from segment import Segment, ContactSegment, get_segmentation, update_segments
from contact_segment_membership import contacts
import itertools
import last_sync

ORDER = 45

SEGMENTATION_NAME = 'Recurring donors'
def delete(_):
    dst = _.destination.connection()
    sql = text("""
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = :sn_name
    """)
    sql = sql.bindparams(sn_name = SEGMENTATION_NAME)
    dst.execute(sql)


def execute(_):
    dst = _.destination.connection()

    sql = text("""
SELECT
    a.contact_id, d.id as donation_id,
    d.started_at, d.ended_at,
    p.receive_date, p.status

FROM donation d
JOIN action a ON a.id = d.action_id
LEFT JOIN payment p ON p.donation_id = d.id

WHERE d.frequency_unit != 'one-off'
ORDER BY contact_id, donation_id, started_at, receive_date
    """)

    segments = get_segmentation(dst, 'Recurring donors')
    payments = dst.execute(sql)
    donors = recurring_donor_contacts(dst)

    acc = []

    for contact_id, all_ps in itertools.groupby(payments, key=lambda r: r['contact_id']):
        all_ps = list(all_ps)
        first_donation = all_ps[0]

        # period from join to first donation
        s = segments['Not a recurring donor']
        cs = ContactSegment(s.segmentation_id, s.segment_id, contact_id,
                            donors[contact_id]['created_at'],
                            first_donation['started_at']) # <- can't be none, we select donors

        if cs.joined_at != cs.left_at:
            acc.insert(0, cs)

        last_donation = None
        for donation_id, ps in itertools.groupby(all_ps, key=lambda r: r['donation_id']):
            ps = list(ps)
            d = ps[0]

            if d['started_at'] == d['ended_at'] or (d['ended_at'] and d['ended_at'] < d['started_at']):
                # if this is 0 duration or runs backwars, skip it
                continue

            if last_donation is not None:
                # We seen an ongoing recurring donation but we get a new one?
                # This record is bogus
                if last_donation['ended_at'] is None:
                    break

                # If this donation is some strange overlap of the previous one, skip it
                # and hope there will come a better day
                if d['started_at'] == last_donation['started_at'] or \
                   d['ended_at'] == last_donation['ended_at'] or \
                   d['started_at'] < last_donation['ended_at']:
                    continue

            ps = list(filter(lambda p: p['status'] is not None, ps))
            ps_succ = list(filter(lambda p: p.status == 'success', ps))


            if last_donation and last_donation['ended_at'] is not None:
                s = segments['Past recurring donor']
                cs = ContactSegment(s.segmentation_id, s.segment_id, contact_id,
                                    last_donation['ended_at'],
                                    d['started_at'])
                acc.insert(0, cs)

            # Generate current of failed donor for this
            segname = None
            if d["ended_at"] is None:
                if len(ps) == 0:
                    segname = 'Current recurring donor'
                else:
                    if len(ps_succ) > 0:
                        segname = 'Current recurring donor'
                    else:
                        segname = 'Failed recurring donor'

            else:
                if len(ps) == 0:
                    segname = 'Failed recurring donor'
                else:
                    if len(ps_succ) > 0:
                        segname = 'Current recurring donor'
                    else:
                        segname = 'Failed recurring donor'

            cs = ContactSegment(segments[segname].segmentation_id, segments[segname].segment_id,
                                contact_id, d['started_at'], d['ended_at'])
            acc.insert(0, cs)

            last_donation = d

        # last period until today, if the person is not current /failed atm
        if last_donation and last_donation['ended_at'] is not None:
            s = segments['Past recurring donor']
            cs = ContactSegment(s.segmentation_id, s.segment_id, contact_id,
                                last_donation['ended_at'], None)
            acc.insert(0, cs)

    update_segments(dst, acc,
                    list(donors.keys()),
                    list(map(lambda s: s.segment_id, segments.values())))


def recurring_donor_contacts(conn):
    recurring_donation_action_takers = text("""
    SELECT
    a.contact_id
    FROM action a
    JOIN donation d ON d.action_id = a.id
    WHERE d.frequency_unit != 'one-off'
    """)

    return contacts(conn, contact_select=recurring_donation_action_takers)
