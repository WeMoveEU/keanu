-- ORDER: 53
-- DELETE FROM open

SET @last_open = 0;
-- BEGIN INCREMENTAL
SET @last_open = (SELECT MAX(external_id) FROM open WHERE external_system = 'civicrm_mailing_event_opened');
-- END INCREMENTAL

INSERT INTO open (broadcast_id, recipient_id, created_at, external_system, external_id)
  SELECT
    b.id, r.id, o.time_stamp, 'civicrm_mailing_event_opened', o.id
  FROM ${SOURCE}.civicrm_mailing_event_opened o
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=o.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=j.mailing_id
  JOIN recipient r ON r.broadcast_id=b.id AND r.contact_id=q.contact_id
  WHERE NOT j.is_test
-- BEGIN INCREMENTAL
  AND o.id > @last_open
-- END INCREMENTAL
;

-- Store broadcasts with new opens to update open counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT DISTINCT broadcast_id AS id FROM open WHERE external_system = 'civicrm_mailing_event_opened' AND external_id > @last_open
;

UPDATE broadcast b JOIN (
    SELECT bt.id AS id, COUNT(DISTINCT o.recipient_id) AS opens
    FROM updated_broadcast bt
    JOIN open o ON bt.id = o.broadcast_id
    GROUP BY bt.id
  ) t ON b.id=t.id
  SET b.open_count = t.opens
;

DROP TABLE updated_broadcast;
