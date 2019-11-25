-- ORDER: 31
-- DELETE FROM action

SELECT @unattributed_donations := id FROM ${SOURCE}.civicrm_campaign WHERE name = 'Unattributed donations';
SELECT @unattributed_donations := id FROM action WHERE external_id = @unattributed_donations;

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

;
