-- ORDER: 52
-- DELETE FROM broadcast_metric WHERE metric = 'recipients'

-- Store which broadcasts are going to be added to recipients table to then update recipient counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT b.id
  FROM broadcast b LEFT JOIN broadcast_metric m ON m.broadcast_id = b.id
  WHERE m.id IS NULL
;

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'recipients', COUNT(DISTINCT contact_id)
  FROM ${SOURCE}.civicrm_mailing_recipients mr
  JOIN broadcast b ON b.external_id = mr.mailing_id AND b.external_system = 'civicrm_mailing'
  JOIN updated_broadcast ub ON b.id = ub.id
  GROUP BY b.id
;

DROP TABLE updated_broadcast;

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'bounces', COUNT(DISTINCT contact_id)
  FROM ${SOURCE}.civicrm_mailing_job j
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.job_id = j.id
  JOIN ${SOURCE}.civicrm_mailing_event_bounce s ON s.event_queue_id = q.id
  JOIN broadcast b ON b.external_id = j.mailing_id AND b.external_system = 'civicrm_mailing'
  WHERE NOT j.is_test
    AND s.bounce_type_id NOT IN (10, 15)
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'spams', COUNT(DISTINCT contact_id)
  FROM ${SOURCE}.civicrm_mailing_job j
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.job_id = j.id
  JOIN ${SOURCE}.civicrm_mailing_event_bounce s ON s.event_queue_id = q.id
  JOIN broadcast b ON b.external_id = j.mailing_id AND b.external_system = 'civicrm_mailing'
  WHERE NOT j.is_test
    AND s.bounce_type_id IN (10, 15)
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;
