from sqlalchemy import text,bindparam
from util import ranges, get_table, nest_sql
from segment import Segment, ContactSegmentAction, get_segmentation, update_segments
from contact_segment_membership import contacts
from datetime import datetime, timedelta
import itertools
import last_sync
import collections

ORDER = 45

SEGMENTATION_NAME = 'Recurring donors'
def delete(_):
    dst = _.destination.connection()
    sql = text("""
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = :sn_name
    """)
    sql = sql.bindparams(sn_name = SEGMENTATION_NAME)
    dst.execute(sql)


DonationInfo = collections.namedtuple("DonationInfo",
                                      ["donation", "payment_count", "success_count", "payments"])

def execute(_):
    dst = _.destination.connection()

    sql = text("""
SELECT
    a.contact_id, d.id as donation_id, a.id as action_id,
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
        contact_payments = list(all_ps)

        donations = [DonationInfo(p[0],
                                  len(list(filter(lambda x: x["status"] is not None, p))),
                                  len(list(filter(lambda x: x["status"] == "success", p))),
                                  p)
                     for donation_id, p in
                     [(donation_id2, list(p2))
                      for donation_id2, p2
                      in itertools.groupby(contact_payments, key=lambda r: r['donation_id'])]]

        donation_by_action_id = {d[0]['action_id']: d for d in donations}

        donations.sort(key=lambda tp: tp.donation['started_at'])

        current_segment = segments['Current recurring donor'] # the 'ok' segment
        failed_segment = segments['Failed recurring donor'] # the 'failed' segment
        
        def cs_from_donation(d):
            ended_at = d.donation['ended_at']
            if d.payment_count > 0 and ended_at is not None and \
               ended_at <= d.donation['started_at']:
                if d.donation['receive_date'] > d.donation['started_at']:
                    ended_at = d.donation['receive_date']
                else:
                    ended_at = d.donation['started_at'] + timedelta(days=1)

            if (ended_at is None and d.payment_count and d.success_count == 0) or \
                 (ended_at is not None and d.payment_count == 0):
                s = failed_segment.segment_id
                cd = ContactSegmentAction(s.segmentation_id, s.segment_id, contact_id,
                                          d.donation["started_at"], ended_at,
                                          d.donation["action_id"])
                return cd
            else:
                s = current_segment
                cd = ContactSegmentAction(s.segmentation_id, s.segment_id, contact_id,
                                          d.donation["started_at"], ended_at,
                                          d.donation["action_id"])
                return cd

        # print("   == donations ===> {} {}".format(donations, contact_payments))
        cs = list(map(cs_from_donation, donations))

        def roll(cs_list, idx=0):
            # check overlap with next element
            if len(cs_list) > idx + 1:
                cur = cs_list[idx]
                nxt = cs_list[idx+1]

                def leave_cur_when_join_nxt():
                    cs_list[idx] = ContactSegmentAction(cur.segmentation_id,
                                                        cur.segment_id,
                                                        cur.contact_id,
                                                        cur.joined_at,
                                                        nxt.joined_at,
                                                        cur.trigger_action_id)


                # overlap can happen because current donation
                # lasts forever:
                if cur.left_at is None:
                    # this covers all fallowing spans
                    if cur.segment_id == current_segment.segment_id:
                        # remove all the newer segments
                        while len(cs_list) != idx + 1:
                            cs_list.pop()
                        return
                    elif cur.segment_id == failed_segment.segment_id:
                        # won't last if there are new segment
                        leave_cur_when_join_nxt()

                    return roll(cs_list, idx+1)

                elif cur.left_at > nxt.joined_at:
                    # overlap can happen if current donation ends after next starts
                    leave_cur_when_join_nxt()
                    return roll(cs_list, idx+1)
                else:
                    # they do not overlap, fine!
                    return roll(cs_list, idx+1)

        roll(cs)

        cs = list(filter(lambda x: x.joined_at != x.left_at, cs))

        fill_cs = []

        s = segments['Not a recurring donor']
        if donors[contact_id]["created_at"] < cs[0].joined_at:
            fill_cs.append(ContactSegmentAction(s.segmentation_id, s.segment_id, contact_id,
                                                donors[contact_id]['created_at'], cs[0].joined_at,
                                                None))
        for i in range(len(cs)):
            # Do not fill in after unclosed span
            if cs[i].left_at is None:
                break

            # check there was a RC with any payment (success or failed)
            if donation_by_action_id[cs[i].trigger_action_id].payment_count > 0:
                # if so, this will be Past recurring donor from now on
                s = segments['Past recurring donor']

            if i + 1 == len(cs):
                # this is the last segment
                left_at = None
            else:
                left_at = cs[i+1].joined_at

            fill_cs.append(ContactSegmentAction(s.segmentation_id, s.segment_id, contact_id,
                                                cs[i].left_at, left_at, None))

        fill_cs = list(filter(lambda x: x.joined_at != x.left_at, fill_cs))
        acc.append(cs)
        acc.append(fill_cs)

        if contact_id in [197116]:
            print("Donor: {}".format(donors[contact_id]))
            print("CS: {}".format(cs))
            print("FILL CS: {}".format(fill_cs))

    update_segments(dst, itertools.chain(*acc),
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
