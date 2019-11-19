-- ORDER: 31
-- DELETE FROM contact_action
-- one-off donate actions
INSERT INTO contact_action
  (contact_id, created_at, action_id, external_id, external_system)

  SELECT
    d.contact_id,
    d.receive_date,
    a.id,
    d.id,
    'civicrm_contribution'

  FROM ${SOURCE}.civicrm_contribution d
  JOIN contact c ON c.id=d.contact_id -- to discard deleted contacts
  JOIN action a ON a.action_type='donate' AND a.external_id = d.campaign_id AND a.external_system = 'civicrm_campaign'
  WHERE NOT d.is_test AND d.contribution_recur_id IS NULL
;

-- recurring donation action
INSERT INTO contact_action
  (contact_id, created_at, action_id, external_id, external_system)

  SELECT
    rd.contact_id,
    rd.create_date,
    a.id as action_id,
    rd.id,
    'civicrm_contribution_recur'

  FROM ${SOURCE}.civicrm_contribution_recur rd
  JOIN contact c ON c.id=rd.contact_id -- to discard deleted contacts
  JOIN action a ON a.action_type='donate' AND a.external_id = rd.campaign_id AND a.external_system = 'civicrm_campaign'
  WHERE NOT rd.is_test
;
