INSERT INTO action
  (campaign_id, action_type, started_at, ended_at, external_id, external_system)
  SELECT
    camp.id,
    'donate',
    c.start_date,
    c.end_date,
    SUBSTR(c.external_identifier FROM 4),
    'houdini'
  FROM wemove_47.civicrm_campaign c
  JOIN wemove_47.civicrm_campaign p ON p.id=c.parent_id
  JOIN campaign camp ON camp.name=p.name COLLATE utf8_general_ci
  WHERE c.external_identifier REGEXP '^cc_[0-9]+$'
;

INSERT INTO action
  (campaign_id, action_type, language, started_at, ended_at, external_id, external_system)
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
    c.start_date,
    c.end_date,
    c.external_identifier,
    IF(c.external_identifier > 10000, 'youmove', 'speakout')
  FROM wemove_47.civicrm_campaign c
  JOIN wemove_47.civicrm_campaign p ON p.id=c.parent_id
  JOIN campaign camp ON camp.name=p.name COLLATE utf8_general_ci
  JOIN wemove_47.civicrm_activity a ON a.campaign_id=c.id
  JOIN wemove_47.civicrm_value_speakout_integration_2 x ON x.entity_id=c.id
  WHERE c.external_identifier NOT LIKE 'cc_%'
    AND a.activity_type_id IN (2, 3, 32, 54, 59, 67)
  GROUP BY c.id, camp.id, activity_type_id
;

