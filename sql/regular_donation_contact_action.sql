-- ORDER: 33
-- regular donation action
-- DELETE contact_action FROM contact_action JOIN action ON contact_action.action_id = action.id WHERE action.action_type = 'regular_donation'


SET @fallback_action = (SELECT a.id from action a join campaign c ON c.id = a.campaign_id
WHERE c.name = 'Other Fundraising' and a.action_type = 'regular_donation');

INSERT INTO contact_action
(contact_id, created_at, action_id, external_id, external_system, source_id)

SELECT
rd.contact_id,
rd.create_date,
COALESCE(a.id, a2.id) as action_id,
rd.id, 'civicrm_contribution_recur',
s.id

FROM
wemove_47.civicrm_contribution_recur rd
JOIN contribution_recur_to_campaign rd2c ON rd.id = rd2c.id
LEFT JOIN action a
   ON a.external_id = rd2c.leaf_campaign_id
   AND a.external_system = 'civicrm_campaign'
   AND a.action_type = 'regular_donation'
JOIN action a2 ON a2.id = @fallback_action

LEFT JOIN
source s ON rd2c.utm_source = s.source
         AND rd2c.utm_medium = s.medium
         AND rd2c.utm_campaign = s.campaign


WHERE
rd.is_test = 0;
-- IGNORE
select count(*) from 
wemove_47.civicrm_contribution_recur rd
WHERE rd.is_test = 0;


select count(*) from contact_action ca JOIN action a ON ca.action_id = a.id
WHERE a.action_type = 'regular_donation';
