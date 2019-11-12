-- ORDER: 9
-- DELETE FROM campaign
INSERT INTO campaign
    (name,  started_at,  campaign_type)
    VALUES
    ('Other Fundraising', '2015-01-01', 'wemove'), -- null medium
    ('Survey Fundraising', '2015-01-01', 'wemove') -- utm_medium=dupal-survey
;

INSERT INTO campaign
    (name, started_at, ended_at, campaign_type, external_id, external_system)
SELECT
    c.name,
    c.start_date,
    c.end_date,
    CASE
    WHEN c.campaign_type_id IN (1,2,3,4,5,7,8,11) THEN 'wemove'
    WHEN c.campaign_type_id IN (6) THEN 'youmove'
    WHEN c.campaign_type_id IN (9,10) THEN 'eci'
    END as campaign_type,
    c.id,
    'civicrm_campaign'
FROM wemove_47.civicrm_campaign c
WHERE
c.id IN (SELECT distinct(id) from goal_campaign)

-- BEGIN INCREMENTAL
 AND c.id NOT IN (SELECT external_id FROM campaign WHERE external_system = 'civicrm_campaign')
-- END INCREMENTAL
    ;
