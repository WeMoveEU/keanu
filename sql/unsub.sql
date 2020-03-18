-- ORDER: 54
-- DELETE FROM unsub
-- DELETE FROM broadcast_metric WHERE metric IN ('unsubs', 'unsub_rate')

SET @last_contact := (SELECT MAX(id) FROM contact);

-- Store which broadcasts are going to be added to unsub table to then update unsub counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT b.id
  FROM broadcast b LEFT JOIN unsub u ON u.broadcast_id = b.id
  WHERE u.id IS NULL
;

INSERT INTO unsub (broadcast_id, contact_id, created_at, external_system, external_id)
  SELECT
    b.id, q.contact_id, u.time_stamp, 'civicrm_mailing_event_unsubscribe', u.id
  FROM ${SOURCE}.civicrm_mailing_event_unsubscribe u
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=u.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=j.mailing_id
  WHERE NOT j.is_test
  AND q.contact_id <= @last_contact
-- BEGIN INCREMENTAL
  AND u.id NOT IN (SELECT external_id FROM unsub WHERE external_system = 'civicrm_mailing_event_unsubscribe')
-- END INCREMENTAL
;

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'unsubs', COUNT(DISTINCT contact_id)
  FROM unsub u
  JOIN broadcast b ON b.id = u.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

DROP TABLE updated_broadcast;

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'unsub_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'unsubs' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;
