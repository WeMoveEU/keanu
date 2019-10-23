-- recurring donation action
INSERT INTO contact_action
  (contact_id, created_at, action_id, source_id, external_id, external_system)

  SELECT
    rd.contact_id,
    rd.create_date,
    a.id as action_id,
    null,
    rd.id,
    'civicrm_contribution_recur'

  FROM wemove_47.civicrm_contribution_recur rd
  JOIN contribution_recur_to_campaign rd2c ON rd.id = rd2c.id
  JOIN action a
    ON a.action_type = 'donate'
    AND a.campaign_id = rd2c.campaign_id
    AND a.language = rd2c.language COLLATE utf8_general_ci

  WHERE rd.is_test = 0
;
