-- ORDER: 55
-- DELETE FROM click
-- DELETE FROM broadcast_metric WHERE metric IN ('clicks', 'clickers')

SET @last_click = 0;
-- BEGIN INCREMENTAL
SET @last_click = (SELECT MAX(external_id) FROM unsub WHERE external_system = 'civicrm_mailing_event_trackable_url_open');
-- END INCREMENTAL

INSERT INTO click (mailing_link_id, contact_id, created_at, external_system, external_id)
  SELECT
    l.id, q.contact_id, c.time_stamp, 'civicrm_mailing_event_trackable_url_open', c.id
  FROM ${SOURCE}.civicrm_mailing_event_trackable_url_open c
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=c.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast_link l ON l.external_system='civicrm_mailing_trackable_url' AND l.external_id=c.trackable_url_id
  WHERE NOT j.is_test
-- BEGIN INCREMENTAL
  AND c.id > @last_click
-- END INCREMENTAL
;

-- Store broadcasts with new clicks to update click counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT broadcast_id AS id
  FROM click c JOIN broadcast_link l ON l.id = c.mailing_link_id
  WHERE c.external_system = 'civicrm_mailing_event_trackable_url_open' AND c.external_id > @last_click
;

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'clickers', COUNT(DISTINCT contact_id)
  FROM click c
  JOIN broadcast_link l ON l.id = c.mailing_link_id
  JOIN broadcast b ON b.id = l.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'clicks', COUNT(c.id)
  FROM click c
  JOIN broadcast_link l ON l.id = c.mailing_link_id
  JOIN broadcast b ON b.id = l.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

DROP TABLE updated_broadcast;
