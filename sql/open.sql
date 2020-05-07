-- ORDER: 53
-- TRUNCATE open
-- DELETE FROM broadcast_metric WHERE metric IN ('openers', 'opens', 'likely_forwarders')

SET @last_open = 0;
SET @last_contact := (SELECT MAX(id) FROM contact);
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
  AND q.contact_id <= @last_contact
-- BEGIN INCREMENTAL
  AND o.id > @last_open
-- END INCREMENTAL
;

-- Store broadcasts with new opens to update open counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT broadcast_id AS id FROM open WHERE external_system = 'civicrm_mailing_event_opened' AND external_id > @last_open
;
CREATE INDEX updated_broadcast_id ON updated_broadcast (id);

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

-- We need Country breakdown for openers_to_recipients, so we need openers
CREATE TEMPORARY TABLE bm_segment AS
  SELECT s.id from segment s JOIN segmentation sn ON sn.id = s.segmentation_id
  WHERE sn.name = 'Country';
CREATE INDEX bm_segment_id ON bm_segment (id);

-- OPENERS
INSERT INTO broadcast_metric -- openers
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @everyone, 'openers', COUNT(DISTINCT o.contact_id)
  FROM open o
  JOIN broadcast b ON b.id = o.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

INSERT INTO broadcast_metric -- openers by country
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, seg.id, 'openers', COUNT(DISTINCT o.contact_id)
  FROM open o
  JOIN broadcast b ON b.id = o.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  JOIN contact_segment cs
    ON cs.contact_id = o.contact_id
    AND cs.joined_at <= b.sent_at
    AND (cs.left_at IS NULL OR b.sent_at < cs.left_at)
  JOIN bm_segment seg
    ON cs.segment_id = seg.id

  GROUP BY b.id, seg.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

-- OPENS
INSERT INTO broadcast_metric -- opens
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'opens', COUNT(o.id)
  FROM open o
  JOIN broadcast b ON b.id = o.broadcast_id
  JOIN updated_broadcast ub ON ub.id = b.id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

-- LIKELY FORWARDERS
INSERT INTO broadcast_metric -- likely_forwarders
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    id, name, @Everyone, 'likely_forwarders', COUNT(contact_id)
  FROM
  (SELECT
     b.id, b.name, o.contact_id
   FROM open o
   JOIN broadcast b ON b.id = o.broadcast_id
   JOIN updated_broadcast ub ON ub.id = b.id
   GROUP BY b.id, b.name, o.contact_id
   HAVING count(o.id) >= 3
  ) forwarders
  GROUP BY id, name

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

DROP TABLE updated_broadcast;

DROP TABLE bm_segment;
