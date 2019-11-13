-- ORDER: 4
-- Use this view to figure out which campaign id is assigned to a Civi CONTRIB RECUR id

DROP VIEW IF EXISTS goal_campaign;

CREATE VIEW goal_campaign AS
SELECT
COALESCE(c3.id, c2.id, c1.id) as id, c1.id as campaign_id
FROM
wemove_47.civicrm_campaign c1
LEFT JOIN wemove_47.civicrm_campaign c2 ON c1.parent_id = c2.id
LEFT JOIN wemove_47.civicrm_campaign c3 ON c2.parent_id = c3.id;

--  --  -- --
DROP VIEW IF EXISTS contribution_recur_to_campaign;


CREATE VIEW contribution_recur_to_campaign AS
SELECT
rd.id,
CASE
  WHEN c.id IS NULL THEN
   CASE
    WHEN utm.utm_medium = 'drupal-survey' THEN
     (SELECT id from campaign where name = 'Survey Fundraising')
    ELSE
     (SELECT id from campaign where name = 'Other Fundraising')
   END
  ELSE c.id
END as campaign_id,
gc.campaign_id as leaf_campaign_id,
m.id as mailing_id,
utm.utm_source,
utm.utm_medium,
utm.utm_campaign

-- useful join for getting campaign by the utm-mailing 

FROM wemove_47.civicrm_contribution_recur rd
LEFT JOIN wemove_47.civicrm_value_recur_utm utm
  ON utm.entity_id = rd.id
LEFT JOIN wemove_47.civicrm_mailing m
  ON (utm.utm_medium = 'email' AND
     substring_index(utm.utm_source, '-', -1) = m.id)
LEFT JOIN wemove_47.civicrm_campaign c_speakout
  ON (utm.utm_medium = 'speakout' AND
     substring_index(utm.utm_source, '-', -1) = c_speakout.external_identifier)
LEFT JOIN goal_campaign gc
  ON gc.campaign_id = COALESCE(m.campaign_id, c_speakout.id)
LEFT JOIN campaign c ON c.external_id = gc.id 

WHERE rd.is_test = 0;

-- ----------------------------------------

DROP VIEW IF EXISTS contribution_to_campaign;

-- Some contributions have sensible campaign_id
-- Some are 'unattributed' campaigns, and then we can
-- use utms (using contribution_to_campaign view) to figure out the campaign and action


CREATE VIEW contribution_to_campaign AS
SELECT
d.id,
CASE
WHEN c.id IS NULL THEN
CASE
WHEN utm.utm_medium_31 = 'drupal-survey' THEN
(SELECT id from campaign where name = 'Survey Fundraising')
ELSE
(SELECT id from campaign where name = 'Other Fundraising')
END
ELSE c.id
END as campaign_id,

gc.campaign_id as leaf_campaign_id,
m.id as mailing_id,
utm.utm_source_30 as source,
utm.utm_medium_31 as medium,
utm.utm_campaign_33 as campaign

FROM wemove_47.civicrm_contribution d
LEFT JOIN wemove_47.civicrm_value_utm_5 utm
     ON utm.entity_id = d.id
LEFT JOIN wemove_47.civicrm_mailing m
     ON (utm.utm_medium_31 = 'email' AND
     substring_index(utm.utm_source_30, '-', -1) = m.id)
LEFT JOIN wemove_47.civicrm_campaign c_speakout
     ON (utm.utm_medium_31 = 'speakout' AND
     substring_index(utm.utm_source_30, '-', -1) = c_speakout.external_identifier)
LEFT JOIN goal_campaign gc
ON gc.campaign_id = COALESCE(CASE WHEN
                              d.campaign_id IN (1360, 2346, 1359)
                              THEN NULL
                              ELSE d.campaign_id
                              END,
                              m.campaign_id,
                              c_speakout.id,
                              d.campaign_id)
LEFT JOIN campaign c ON c.external_id = gc.id 
;
