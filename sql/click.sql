-- ORDER: 56
-- DELETE FROM click

SET @last_click = 0;
-- BEGIN INCREMENTAL
SET @last_click = (SELECT MAX(external_id) FROM unsub WHERE external_system = 'civicrm_mailing_event_trackable_url_open');
-- END INCREMENTAL

INSERT INTO click (mailing_link_id, recipient_id, created_at, external_system, external_id)
  SELECT
    l.id, r.id, c.time_stamp, 'civicrm_mailing_event_trackable_url_open', c.id
  FROM ${SOURCE}.civicrm_mailing_event_trackable_url_open c
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=c.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast_link l ON l.external_system='civicrm_mailing_trackable_url' AND l.external_id=c.trackable_url_id
  JOIN recipient r ON r.broadcast_id=l.broadcast_id AND r.contact_id=q.contact_id
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

UPDATE broadcast b JOIN (
    SELECT bt.id AS id, COUNT(DISTINCT c.recipient_id) AS clicks
    FROM updated_broadcast bt
    JOIN broadcast_link l ON bt.id = l.broadcast_id
    JOIN click c ON l.id = c.mailing_link_id
    GROUP BY bt.id
  ) t ON b.id=t.id
  SET b.click_count = t.clicks
;

DROP TABLE updated_broadcast;
