-- ORDER: 54
-- DELETE FROM unsub

INSERT INTO unsub (broadcast_id, recipient_id, created_at, external_system, external_id)
  SELECT
    b.id, r.id, u.time_stamp, 'civicrm_mailing_event_unsubscribe', u.id
  FROM ${SOURCE}.civicrm_mailing_event_unsubscribe u
  JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.id=u.event_queue_id
  JOIN ${SOURCE}.civicrm_mailing_job j ON j.id=q.job_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=j.mailing_id
  JOIN recipient r ON r.broadcast_id=b.id AND r.contact_id=q.contact_id
  WHERE NOT j.is_test
-- BEGIN INCREMENTAL
  AND u.id NOT IN (SELECT external_id FROM unsub WHERE external_system = 'civicrm_mailing_event_unsubscribe')
-- END INCREMENTAL
;
