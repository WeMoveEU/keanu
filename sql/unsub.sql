-- ORDER: 54
-- DELETE FROM unsub
-- DELETE FROM broadcast_metric WHERE metric IN ('unsubs', 'unsub_rate')

-- Country breakdown also for metrics:
-- unsub_rate

SET @last_unsub := 0;
SET @last_contact := (SELECT MAX(id) FROM contact);
-- BEGIN INCREMENTAL
SET @last_unsub := (SELECT MAX(external_id) FROM unsub WHERE external_system = 'civicrm_mailing_event_unsubscribe');
-- END INCREMENTAL

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
  AND u.id > @last_unsub
-- END INCREMENTAL
;

-- Store broadcasts with new unsubs to update unsub counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT broadcast_id AS id FROM unsub WHERE external_system = 'civicrm_mailing_event_unsubscribe' AND external_id > @last_unsub
;

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');
CREATE TEMPORARY TABLE bm_segment AS
  SELECT @everyone AS id
  UNION
  SELECT s.id from segment s JOIN segmentation sn ON sn.id = s.segmentation_id
  WHERE sn.name = 'Country';
CREATE INDEX bm_segment_id ON bm_segment (id);

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, seg.id, 'unsubs', COUNT(DISTINCT u.contact_id)
  FROM unsub u
  JOIN broadcast b ON b.id = u.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  JOIN bm_segment seg
  JOIN contact_segment cs
    ON u.contact_id = cs.contact_id
    AND cs.segment_id = seg.id
    AND cs.joined_at <= b.sent_at
    AND (cs.left_at IS NULL OR b.sent_at < cs.left_at)

  GROUP BY b.id, seg.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

DROP TABLE updated_broadcast;
