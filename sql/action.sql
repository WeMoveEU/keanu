-- ORDER: 30
-- DELETE FROM action
INSERT INTO action
    (campaign_id, action_type, language, external_id, external_system)
SELECT
    camp.id,
    CASE
    WHEN activity_type_id = 2 THEN 'call'
    WHEN activity_type_id = 3 THEN 'email'
    WHEN activity_type_id = 6 THEN 'donation'
    WHEN activity_type_id = 32 THEN 'sign'
    WHEN activity_type_id = 54 THEN 'share'
    WHEN activity_type_id = 59 THEN 'tweet'
    WHEN activity_type_id = 67 THEN 'facebook'
    END AS action_type,
    x.language_4,
    c.id,
    'civicrm_campaign'
FROM wemove_47.civicrm_campaign c
    JOIN goal_campaign g ON g.campaign_id=c.id
    JOIN campaign camp ON camp.external_id=g.id
    JOIN wemove_47.civicrm_activity a ON a.campaign_id=c.id
    JOIN wemove_47.civicrm_value_speakout_integration_2 x ON x.entity_id=c.id
WHERE a.activity_type_id IN (2, 3, 6, 32, 54, 59, 67)

-- BEGIN INCREMENTAL
AND NOT c.id IN (SELECT external_id from action where external_system = 'civicrm_campaign')
-- END INCREMENTAL

GROUP BY c.id, camp.id, activity_type_id
    ;


-- Create regular_donation action for every Contribution Recur that cant be tracked by utm
-- the contribution_recur_to_campaign VIEW holds the logic 
INSERT INTO action
    (campaign_id, action_type, external_id, external_system, language)
SELECT
    distinct
    c.id,
    'regular_donation',
    rd2c.leaf_campaign_id,
    CASE rd2c.leaf_campaign_id WHEN NULL THEN NULL ELSE 'civicrm_campaign' END,
    x.language_4 as language
FROM
    contribution_recur_to_campaign rd2c
    JOIN
    campaign c ON rd2c.campaign_id = c.id
    LEFT JOIN wemove_47.civicrm_value_speakout_integration_2 x
    ON x.entity_id = rd2c.leaf_campaign_id

    ;

INSERT INTO action
(campaign_id, action_type)
SELECT
c.id, 'donation'
FROM campaign c
where c.name = 'Other Fundraising';

-- IGNORE
-- we should have all of the donatons actions created by the first query ^

INSERT INTO action
    (campaign_id, action_type, external_id, external_system, language)
SELECT
    distinct
    c.id,
    'donation',
    d2c.leaf_campaign_id,
    CASE d2c.leaf_campaign_id WHEN NULL THEN NULL ELSE 'civicrm_campaign' END,
    x.language_4 as language
FROM
  contribution_to_campaign d2c
  JOIN
  campaign c ON d2c.campaign_id = c.id;
  LEFT JOIN wemove_47.civicrm_value_speakout_integration_2 x
       ON x.entity_id = d2c.leaf_campaign_id;

