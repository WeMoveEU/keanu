-- ORDER: 56
-- DELETE FROM click

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
