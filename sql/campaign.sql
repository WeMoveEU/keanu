-- ORDER: 9
-- DELETE FROM campaign

INSERT INTO campaign
  (id, name, started_at, ended_at, campaign_type, external_id, external_system)
  SELECT
    c.id, -- Introducing identity with source
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
FROM ${SOURCE}.civicrm_campaign c
WHERE c.id=c.parent_id

-- BEGIN INCREMENTAL
AND c.id NOT IN (SELECT external_id FROM campaign WHERE external_system = 'civicrm_campaign')
-- END INCREMENTAL
    ;


-- BEGIN INCREMENTAL
-- Update what could change:
UPDATE campaign c
    JOIN ${SOURCE}.civicrm_campaign civic
    ON c.external_system = 'civicrm_campaign' AND c.external_id = civic.id
SET
    c.ended_at = civic.end_date,
    c.name = civic.name
;
-- END INCREMENTAL

