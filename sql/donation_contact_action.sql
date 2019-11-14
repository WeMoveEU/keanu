-- ORDER: 35
-- DELETE ca FROM contact_action ca JOIN action a ON ca.action_id = a.id WHERE a.action_type = 'donation'

SET @fallback_action = (SELECT a.id from action a join campaign c ON c.id = a.campaign_id
                             WHERE c.name = 'Other Fundraising' and a.action_type = 'donation');

INSERT INTO
contact_action
 (action_id, contact_id, created_at, external_id, external_system, source_id)
SELECT
 COALESCE(a.id, a2.id) as action_id,
 cont.id as contact_id,
 c.receive_date,
 c.id as external_id, 'civicrm_contribution',
 s.id as source_id

FROM
wemove_47.civicrm_contribution c
JOIN contact cont ON cont.id = c.contact_id
JOIN contribution_to_campaign d2c ON c.id = d2c.id
LEFT JOIN action a
ON a.external_id = d2c.leaf_campaign_id
AND a.external_system = 'civicrm_campaign'
AND a.action_type = 'donation'
JOIN action a2 ON a2.id = @fallback_action
LEFT JOIN source s ON d2c.source = s.source AND d2c.medium = s.medium AND d2c.campaign = s.campaign

WHERE
c.is_test = 0 AND c.contribution_status_id = 1 AND c.contribution_recur_id IS NULL;
