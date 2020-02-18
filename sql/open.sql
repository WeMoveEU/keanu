-- ORDER: 53
-- TRUNCATE open
-- DELETE FROM broadcast_metric WHERE metric IN ('openers', 'opens')

SET @last_open = 0;
-- BEGIN INCREMENTAL
SET @last_open = (SELECT MAX(external_id) FROM open WHERE external_system = 'civicrm_mailing_event_opened');
-- END INCREMENTAL

INSERT INTO open (broadcast_id, contact_id, created_at, external_system, external_id)
  SELECT
    b.id, q.contact_id, o.time_stamp, 'civicrm_mailing_event_opened', o.id
  FROM ${SOURCE}.civicrm_mailing_event_opened o
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=o.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=j.mailing_id
  WHERE NOT j.is_test
-- BEGIN INCREMENTAL
  AND o.id > @last_open
-- END INCREMENTAL
;

-- Store broadcasts with new opens to update open counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT broadcast_id AS id FROM open WHERE external_system = 'civicrm_mailing_event_opened' AND external_id > @last_open
;

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'openers', COUNT(DISTINCT contact_id)
  FROM open o
  JOIN broadcast b ON b.id = o.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'opens', COUNT(o.id)
  FROM open o
  JOIN broadcast b ON b.id = o.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

DROP TABLE updated_broadcast;
