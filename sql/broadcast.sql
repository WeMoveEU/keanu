-- ORDER: 51
-- DELETE FROM broadcast;

INSERT INTO broadcast 
  (id, name, broadcast_type, language, sent_at, broadcast_test_id, campaign_id, external_id, external_system)
  SELECT
    m.id, -- identity with source
    m.name, 'email', m.language, m.scheduled_date, t.id, camp.id, m.id, 'civicrm_mailing'
  FROM ${SOURCE}.civicrm_mailing m
  JOIN ${SOURCE}.civicrm_campaign c ON c.id=m.campaign_id
  JOIN campaign camp ON c.parent_id=camp.external_id AND camp.external_system='civicrm_campaign'
  LEFT JOIN ${SOURCE}.civicrm_mailing_abtest ab ON m.id IN (mailing_id_a, mailing_id_b)
  LEFT JOIN broadcast_test t ON t.external_id=ab.id AND t.external_system='civicrm_mailing_abtest'
  WHERE scheduled_date IS NOT NULL AND language IS NOT NULL
-- BEGIN INCREMENTAL
  AND m.id NOT IN (SELECT external_id FROM broadcast WHERE external_system = 'civicrm_mailing')
-- END INCREMENTAL
;

