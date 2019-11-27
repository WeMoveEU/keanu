-- ORDER: 53
-- DELETE FROM open

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
