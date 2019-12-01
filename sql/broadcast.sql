-- ORDER: 51
-- DELETE FROM broadcast;

INSERT INTO broadcast 
  (name, broadcast_type, sent_at, broadcast_test_id, campaign_id, external_id, external_system)
  SELECT
    m.name, 'email', scheduled_date, t.id, camp.id, m.id, 'civicrm_mailing'
  FROM ${SOURCE}.civicrm_mailing m
  JOIN ${SOURCE}.civicrm_campaign c ON c.id=m.campaign_id
  JOIN campaign camp ON c.parent_id=camp.external_id AND camp.external_system='civicrm_campaign'
  LEFT JOIN ${SOURCE}.civicrm_mailing_abtest ab ON m.id IN (mailing_id_a, mailing_id_b)
  LEFT JOIN broadcast_test t ON t.external_id=ab.id AND t.external_system='civicrm_mailing_abtest'
  WHERE scheduled_date IS NOT NULL
-- BEGIN INCREMENTAL
  AND m.id NOT IN (SELECT external_id FROM broadcast WHERE external_system = 'civicrm_mailing')
-- END INCREMENTAL
;

UPDATE broadcast b JOIN (
    SELECT
      j.mailing_id,
      SUM(s.bounce_type_id NOT IN (10, 15)) AS bounces,
      SUM(s.bounce_type_id IN (10, 15)) AS spams
    FROM ${SOURCE}.civicrm_mailing_job j
    JOIN ${SOURCE}.civicrm_mailing_event_queue q ON q.job_id = j.id
    JOIN ${SOURCE}.civicrm_mailing_event_bounce s ON s.event_queue_id = q.id
    WHERE NOT j.is_test
    GROUP BY j.mailing_id
  ) t ON t.mailing_id = b.external_id AND b.external_system = 'civicrm_mailing'
  SET b.bounce_count = bounces, b.spam_count = t.spams
;
