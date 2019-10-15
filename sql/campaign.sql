INSERT INTO campaign 
(name,  started_at,  campaign_type, external_system)
VALUES
('Other Fundraising', '2015-01-01', 'member', 'civicrm'), -- null medium
('Survey Fundraising', '2015-01-01', 'member', 'civicrm'); -- utm_medium=dupal-survey

INSERT INTO
campaign
(name, parent_id, started_at, ended_at, language, campaign_type, external_id, external_system)

SELECT
c.name,
NULL as parent_id,
c.start_date,
c.end_date,
NULL as language,
CASE
 WHEN c.campaign_type_id IN (1,2,3,4,5,7,8,11) THEN 'member'
 WHEN c.campaign_type_id IN (6) THEN 'distributed'
 WHEN c.campaign_type_id IN (9) THEN 'eci'
 WHEN c.campaign_type_id IN (10) THEN 'nomember'
END as campaign_type,
c.id as external_id, 'civicrm'

FROM
wemove_47.civicrm_campaign c
;

