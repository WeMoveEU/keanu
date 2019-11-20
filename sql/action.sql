-- ORDER: 30
-- DELETE FROM action

-- BEGIN INITIAL
SELECT @unattributed := id FROM campaign WHERE name = 'Unattributed';
SELECT @unattributed_donations := id FROM ${SOURCE}.civicrm_campaign WHERE name = 'Unattributed donations';

INSERT INTO action (campaign_id, action_type, external_id, external_system) VALUES
  (@unattributed, 'donate', @unattributed_donations, 'civicrm_campaign')
;
-- END INITIAL

INSERT INTO action
  (campaign_id, action_type, language, external_id, external_system)
  SELECT
    camp.id,
    CASE
    WHEN activity_type_id = 2 THEN 'call'
    WHEN activity_type_id = 3 THEN 'email'
    WHEN activity_type_id = 32 THEN 'sign'
    WHEN activity_type_id = 54 THEN 'share'
    WHEN activity_type_id = 59 THEN 'tweet'
    WHEN activity_type_id = 67 THEN 'facebook'
    END AS action_type,
    x.language_4,
    c.id,
    'civicrm_campaign'

  FROM ${SOURCE}.civicrm_campaign c
  JOIN ${SOURCE}.civicrm_campaign p ON p.id=c.parent_id
  JOIN campaign camp ON camp.external_id=p.id
  JOIN ${SOURCE}.civicrm_activity a ON a.campaign_id=c.id
  JOIN ${SOURCE}.civicrm_value_speakout_integration_2 x ON x.entity_id=c.id

  WHERE a.activity_type_id IN (2, 3, 32, 54, 59, 67)
-- BEGIN INCREMENTAL
AND c.id NOT IN (SELECT external_id FROM action WHERE external_system = 'civicrm_campaign')
-- END INCREMENTAL
  GROUP BY c.id, camp.id, activity_type_id
;

-- Create donate action for every contribution and contribution recur
INSERT INTO action
  (campaign_id, action_type, language, external_id, external_system)
  SELECT
    DISTINCT
    camp.id, 'donate', x.language_4, c.id, 'civicrm_campaign'
  FROM ${SOURCE}.civicrm_campaign c
  JOIN ${SOURCE}.civicrm_campaign p ON p.id=c.parent_id
  JOIN campaign camp ON camp.external_id=p.id
  JOIN (
      SELECT d.campaign_id
      FROM ${SOURCE}.civicrm_contribution d
      UNION
      SELECT rd.campaign_id 
      FROM ${SOURCE}.civicrm_contribution_recur rd 
      ) d ON d.campaign_id=c.id
  JOIN ${SOURCE}.civicrm_value_speakout_integration_2 x ON x.entity_id=c.id
-- BEGIN INCREMENTAL
  WHERE c.id NOT IN (SELECT external_id FROM action WHERE external_system = 'civicrm_campaign' AND action_type = 'donate')
-- END INCREMENTAL
  GROUP BY c.id, camp.id
;

-- other updates: can language change?
