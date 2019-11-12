-- ORDER: 33
-- regular donation action
-- DELETE contact_action FROM contact_action JOIN action ON contact_action.action_id = action.id WHERE action.action_type = 'regular_donation'
INSERT INTO contact_action
(contact_id, created_at, action_id, external_id, source_id)

SELECT
rd.contact_id,
rd.create_date,
a.id as action_id,
rd.id, s.id

FROM
wemove_47.civicrm_contribution_recur rd
JOIN contribution_recur_to_campaign rd2c ON rd.id = rd2c.id
JOIN action a ON
   a.action_type = 'regular_donation'
   AND a.campaign_id = rd2c.campaign_id
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
