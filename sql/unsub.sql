-- ORDER: 54
-- DELETE FROM unsub

-- Store which broadcasts are going to be added to unsub table to then update unsub counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT b.id
  FROM broadcast b LEFT JOIN unsub u ON u.broadcast_id = b.id
  WHERE u.id IS NULL
;

INSERT INTO unsub (broadcast_id, recipient_id, created_at, external_system, external_id)
  SELECT
    b.id, r.id, u.time_stamp, 'civicrm_mailing_event_unsubscribe', u.id
  FROM ${SOURCE}.civicrm_mailing_event_unsubscribe u
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=u.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=j.mailing_id
  JOIN recipient r ON r.broadcast_id=b.id AND r.contact_id=q.contact_id
  WHERE NOT j.is_test
-- BEGIN INCREMENTAL
  AND u.id NOT IN (SELECT external_id FROM unsub WHERE external_system = 'civicrm_mailing_event_unsubscribe')
-- END INCREMENTAL
;

UPDATE broadcast b JOIN (
    SELECT bt.id AS id, COUNT(DISTINCT u.recipient_id) AS unsubs
    FROM updated_broadcast bt
    JOIN unsub u ON bt.id = u.broadcast_id
    GROUP BY bt.id
  ) t ON b.id=t.id
  SET b.unsub_count = t.unsubs
;

DROP TABLE updated_broadcast;
