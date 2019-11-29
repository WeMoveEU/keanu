-- ORDER: 31
-- DELETE FROM action

SELECT @unattributed_donations := a.id FROM action_page a JOIN campaign c ON a.campaign_id = c.id where a.action_type = 'donate' and c.name = 'Unattributed';

-- one-off donate actions
INSERT INTO action
  (contact_id, created_at, action_page_id, external_id, external_system)

  SELECT
    d.contact_id,
    d.receive_date,
    COALESCE(a.id, @unattributed_donations),
    d.id,
    'civicrm_contribution'

  FROM ${SOURCE}.civicrm_contribution d
  JOIN contact c ON c.id=d.contact_id -- to discard deleted contacts
  LEFT JOIN action_page a ON a.action_type='donate' AND a.external_id = d.campaign_id AND a.external_system = 'civicrm_campaign'
WHERE NOT d.is_test AND d.contribution_recur_id IS NULL
-- BEGIN INCREMENTAL
AND d.id NOT IN (SELECT external_id FROM action WHERE external_system = 'civicrm_contribution')
-- END INCREMENTAL
;

-- recurring donation action
INSERT INTO action
  (contact_id, created_at, action_page_id, external_id, external_system)

  SELECT
    rd.contact_id,
    rd.create_date,
    COALESCE(a.id, @unattributed_donations),
    rd.id,
    'civicrm_contribution_recur'

  FROM ${SOURCE}.civicrm_contribution_recur rd
  JOIN contact c ON c.id=rd.contact_id -- to discard deleted contacts
  JOIN action_page a ON a.action_type='donate' AND a.external_id = rd.campaign_id AND a.external_system = 'civicrm_campaign'
  WHERE NOT rd.is_test
  -- BEGIN INCREMENTAL
      AND rd.id NOT IN (SELECT external_id FROM action WHERE external_system = 'civicrm_contribution_recur')
  -- END INCREMENTAL

-- Activities
INSERT INTO action
  (contact_id, created_at, action_page_id, external_id, external_system)

  SELECT
    ac.contact_id, activity_date_time, ap.id, a.id, 'civicrm_activity'
  FROM ${SOURCE}.civicrm_activity a
  JOIN ${SOURCE}.civicrm_activity_contact ac ON ac.activity_id = a.id AND ac.record_type_id = 2
  JOIN action_page ap ON ap.external_id = a.campaign_id AND ap.external_system = 'civicrm_campaign' AND ap.action_type = CASE
      WHEN activity_type_id = 2 THEN 'call'
      WHEN activity_type_id = 3 THEN 'email'
      WHEN activity_type_id = 32 THEN 'sign'
      WHEN activity_type_id = 54 THEN 'share'
      WHEN activity_type_id = 59 THEN 'tweet'
      WHEN activity_type_id = 67 THEN 'facebook'
    END
  WHERE a.activity_type_id IN (2, 3, 32, 54, 59, 67)
  -- BEGIN INCREMENTAL
    AND a.id NOT IN (SELECT external_id FROM action WHERE external_system = 'civicrm_activity')
  -- END INCREMENTAL
;
