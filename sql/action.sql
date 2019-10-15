-- regular donations action

INSERT INTO action
(campaign_id, action_type, external_id)

SELECT
distinct
c.id,
'regular_donation',
c.external_id

FROM
contribution_recur_to_campaign rd2c
JOIN
campaign c ON rd2c.campaign_id = c.id
;
