-- ORDER: 50
-- DELETE FROM broadcast_test

INSERT INTO broadcast_test (id, name, created_at, sent_at, external_id, external_system)
  SELECT
    ab.id, -- identity with the source
    ab.name, ab.created_date, ma.scheduled_date, ab.id, 'civicrm_mailing_abtest'
  FROM ${SOURCE}.civicrm_mailing_abtest ab
  JOIN ${SOURCE}.civicrm_mailing ma ON ma.id=ab.mailing_id_a
  WHERE ma.scheduled_date IS NOT NULL
-- BEGIN INCREMENTAL
  AND ab.id NOT IN (SELECT external_id FROM broadcast_test WHERE external_system = 'civicrm_mailing_abtest')
-- END INCREMENTAL
;

