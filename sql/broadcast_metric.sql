-- ORDER: 56
-- DELETE FROM broadcast_metric WHERE metric IN ('recipients', 'spams', 'bounces', 'conversions', 'converted', 'sharers', 'shares')

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

-- RECIPIENTS
-- Store which broadcasts are going to be added to recipients table to then update recipient counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT b.id
  FROM broadcast b LEFT JOIN broadcast_metric m ON m.broadcast_id = b.id AND m.metric = 'recipients'
  WHERE m.id IS NULL
;

-- Country breakdown also for metrics:
-- recipients
CREATE TEMPORARY TABLE bm_segment AS
  SELECT @everyone AS id
  UNION
  SELECT s.id from segment s JOIN segmentation sn ON sn.id = s.segmentation_id
  WHERE sn.name = 'Country';
CREATE INDEX bm_segment_id ON bm_segment (id);

-- RECIPIENTS
INSERT INTO broadcast_metric -- recipients
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b.id, b.name, seg.id, 'recipients', COUNT(DISTINCT mr.contact_id)
  FROM ${SOURCE}.civicrm_mailing_recipients mr
         JOIN broadcast b ON b.external_id = mr.mailing_id AND b.external_system = 'civicrm_mailing'
         JOIN updated_broadcast ub ON b.id = ub.id
         JOIN bm_segment seg
         JOIN contact_segment cs
             ON mr.contact_id = cs.contact_id
             AND cs.segment_id = seg.id
             AND cs.joined_at <= b.sent_at
             AND (cs.left_at IS NULL OR b.sent_at < cs.left_at)
  GROUP BY b.id, seg.id
;

DROP TABLE updated_broadcast;

-- BOUNCES
INSERT INTO broadcast_metric -- bounces
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'bounces', COUNT(DISTINCT contact_id)
  FROM ${SOURCE}.civicrm_mailing_job j
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.job_id = j.id
  JOIN ${SOURCE}.civicrm_mailing_event_bounce s ON s.event_queue_id = q.id
  JOIN broadcast b ON b.external_id = j.mailing_id AND b.external_system = 'civicrm_mailing'
  WHERE NOT j.is_test
    AND s.bounce_type_id NOT IN (10, 15)
-- BEGIN INCREMENTAL
    AND DATEDIFF(NOW(), b.sent_at) <= 10
-- END INCREMENTAL
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

-- SPAMS
INSERT INTO broadcast_metric -- spams
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'spams', COUNT(DISTINCT contact_id)
  FROM ${SOURCE}.civicrm_mailing_job j
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.job_id = j.id
  JOIN ${SOURCE}.civicrm_mailing_event_bounce s ON s.event_queue_id = q.id
  JOIN broadcast b ON b.external_id = j.mailing_id AND b.external_system = 'civicrm_mailing'
  WHERE NOT j.is_test
    AND s.bounce_type_id IN (10, 15)
-- BEGIN INCREMENTAL
    AND DATEDIFF(NOW(), b.sent_at) <= 10
-- END INCREMENTAL
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

-- OTHER BASE METRICS FOR BROADCAST:
-- OPENS and LIKELY FORWARDERS in open.sql
-- CLICKS in click.sql
-- UNSUBS in unsub.sql

-- CONVERSIONS
INSERT INTO broadcast_metric -- converted
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b.id, b.name, seg.id, 'converted', COUNT(DISTINCT a.contact_id)
  FROM action a
         JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type != 'consent'
         JOIN broadcast_link l ON l.source_id = a.source_id
         JOIN broadcast b ON b.id = l.broadcast_id
         JOIN bm_segment seg
         JOIN contact_segment cs
             ON a.contact_id = cs.contact_id
             AND cs.segment_id = seg.id
             AND cs.joined_at <= b.sent_at
             AND (cs.left_at IS NULL OR b.sent_at < cs.left_at)
-- BEGIN INCREMENTAL
  AND DATEDIFF(NOW(), b.sent_at) <= 10
-- END INCREMENTAL

  GROUP BY b.id, seg.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;


INSERT INTO broadcast_metric -- conversions
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'conversions', COUNT(a.id)
  FROM action a
  JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type != 'consent'
  JOIN broadcast_link l ON l.source_id = a.source_id
  JOIN broadcast b ON b.id = l.broadcast_id
-- BEGIN INCREMENTAL
  WHERE DATEDIFF(NOW(), b.sent_at) <= 10
-- END INCREMENTAL
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;


-- SHARES
INSERT INTO broadcast_metric -- sharers
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b.id, b.name, @Everyone, 'sharers', COUNT(DISTINCT contact_id)
  FROM action a
         JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type = 'share'
         JOIN broadcast_link l ON l.source_id = a.source_id
         JOIN broadcast b ON b.id = l.broadcast_id
  -- BEGIN INCREMENTAL
             AND DATEDIFF(NOW(), b.sent_at) <= 10
  -- END INCREMENTAL

 GROUP BY b.id

          ON DUPLICATE KEY UPDATE value=VALUES(value)
          ;

INSERT INTO broadcast_metric -- shares
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b.id, b.name, @Everyone, 'shares', COUNT(a.id)
  FROM action a
         JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type = 'share'
         JOIN broadcast_link l ON l.source_id = a.source_id
         JOIN broadcast b ON b.id = l.broadcast_id
  -- BEGIN INCREMENTAL
 WHERE DATEDIFF(NOW(), b.sent_at) <= 10
  -- END INCREMENTAL
 GROUP BY b.id

          ON DUPLICATE KEY UPDATE value=VALUES(value)
          ;

DROP TABLE bm_segment;
