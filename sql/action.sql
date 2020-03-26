-- ORDER: 31
-- DELETE FROM consent
-- DELETE FROM action
-- DELETE FROM campaign_metric WHERE metric IN ('actions', 'shares', 'donations', 'new_members')

SELECT @unattributed_donations := a.id FROM action_page a JOIN campaign c ON a.campaign_id = c.id where a.action_type = 'donate' and c.name = 'Unattributed';
SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');
SET @last_contact := (SELECT MAX(id) FROM contact);
SET @last_action := (SELECT COALESCE(MAX(id), 0) FROM action);

-- one-off donate actions
SET @last_id := (SELECT last_sync_id('action', 'civicrm_contribution'));
INSERT INTO action
  (contact_id, created_at, action_page_id, source_id, external_id, external_system)

  SELECT
    d.contact_id,
    d.receive_date,
    COALESCE(a.id, @unattributed_donations),
    s.id,
    d.id,
    'civicrm_contribution'

  FROM ${SOURCE}.civicrm_contribution d
  LEFT JOIN action_page a ON a.action_type='donate' AND a.external_id = d.campaign_id AND a.external_system = 'civicrm_campaign'
  LEFT JOIN ${SOURCE}.civicrm_value_utm_5 utm ON utm.entity_id = d.id
  LEFT JOIN source s ON s.source = utm.utm_source_30 COLLATE utf8_general_ci
                    AND s.medium = utm.utm_medium_31 COLLATE utf8_general_ci
                    AND s.campaign = utm.utm_campaign_33 COLLATE utf8_general_ci
  WHERE NOT d.is_test AND d.contribution_recur_id IS NULL
  AND d.contact_id <= @last_contact
-- BEGIN INCREMENTAL
  AND d.id > @last_id
-- END INCREMENTAL
;

SELECT save_last_sync_id('action', 'civicrm_contribution',
  (SELECT max(external_id) from action WHERE external_system = 'civicrm_contribution'));

-- recurring donation action
SET @last_id := (SELECT last_sync_id('action', 'civicrm_contribution_recur'));
INSERT INTO action
  (contact_id, created_at, action_page_id, source_id, external_id, external_system)

  SELECT
    rd.contact_id,
    rd.create_date,
    COALESCE(a.id, @unattributed_donations),
    s.id,
    rd.id,
    'civicrm_contribution_recur'

  FROM ${SOURCE}.civicrm_contribution_recur rd
  LEFT JOIN action_page a ON a.action_type='donate' AND a.external_id = rd.campaign_id AND a.external_system = 'civicrm_campaign'
  LEFT JOIN ${SOURCE}.civicrm_value_recur_utm utm ON utm.entity_id = rd.id
  LEFT JOIN source s ON s.source = utm.utm_source COLLATE utf8_general_ci
                    AND s.medium = utm.utm_medium COLLATE utf8_general_ci
                    AND s.campaign = utm.utm_campaign COLLATE utf8_general_ci
  WHERE NOT rd.is_test
  AND rd.contact_id <= @last_contact
  -- BEGIN INCREMENTAL
  AND rd.id > @last_id
  -- END INCREMENTAL
;
SELECT save_last_sync_id('action', 'civicrm_contribution_recur',
  (SELECT max(external_id) from action WHERE external_system = 'civicrm_contribution_recur'));

-- Activities
SET @last_id := (SELECT last_sync_id('action', 'civicrm_activity'));
INSERT INTO action
  (contact_id, created_at, action_page_id, source_id, external_id, external_system)

  SELECT
    ac.contact_id, activity_date_time, ap.id, s.id, a.id, 'civicrm_activity'
  FROM ${SOURCE}.civicrm_activity a
  JOIN ${SOURCE}.civicrm_activity_contact ac ON ac.activity_id = a.id AND ac.record_type_id = 2
  JOIN action_page ap ON ap.external_id = a.campaign_id AND ap.external_system = 'civicrm_campaign' AND ap.action_type = CASE
      WHEN activity_type_id = 2 THEN 'call'
      WHEN activity_type_id = 3 THEN 'email'
      WHEN activity_type_id = 32 THEN 'sign'
      WHEN activity_type_id = 54 THEN 'share'
      WHEN activity_type_id = 59 THEN 'tweet'
      WHEN activity_type_id = 67 THEN 'facebook'
    END
  LEFT JOIN ${SOURCE}.civicrm_value_action_source_4 utm ON utm.entity_id = a.id
  LEFT JOIN source s ON s.source = utm.source_27 COLLATE utf8_general_ci
                    AND s.medium = utm.media_28 COLLATE utf8_general_ci
                    AND s.campaign = utm.campaign_26 COLLATE utf8_general_ci
  WHERE a.activity_type_id IN (2, 3, 32, 54, 59, 67)
  AND ac.contact_id <= @last_contact
  -- BEGIN INCREMENTAL
  AND a.id > @last_id
  -- END INCREMENTAL
;
SELECT save_last_sync_id('action', 'civicrm_activity',
  (SELECT max(external_id) from action WHERE external_system = 'civicrm_activity'));

-- Consents
-- BEGIN INCREMENTAL
SET @last_id := (SELECT last_sync_id('action', 'civicrm_activity.consent'));

CREATE TEMPORARY TABLE growthy_campaign (id INT PRIMARY KEY);
-- END INCREMENTAL

INSERT INTO action
  (contact_id, created_at, action_page_id, source_id, external_id, external_system)

  SELECT
    ac.contact_id, activity_date_time, ap.id, s.id, a.id, 'civicrm_activity'
  FROM ${SOURCE}.civicrm_activity a
  JOIN ${SOURCE}.civicrm_activity_contact ac ON ac.activity_id = a.id AND ac.record_type_id = 2
  JOIN action_page ap ON ap.external_id = a.campaign_id AND ap.external_system = 'civicrm_campaign' AND ap.action_type = 'consent'
  LEFT JOIN ${SOURCE}.civicrm_value_action_source_4 utm ON utm.entity_id = a.id
  LEFT JOIN source s ON s.source = utm.source_27 COLLATE utf8_general_ci
                    AND s.medium = utm.media_28 COLLATE utf8_general_ci
                    AND s.campaign = utm.campaign_26 COLLATE utf8_general_ci
  WHERE a.activity_type_id IN (2, 3, 32, 54, 59, 67) AND a.status_id IN (1, 4, 9)
  AND ac.contact_id <= @last_contact
  -- BEGIN INCREMENTAL
  AND a.id > @last_id
  -- END INCREMENTAL
;

INSERT INTO consent
  (action_id, status)

  SELECT
    a.id,
    CASE
    WHEN status_id = 1 THEN 'pending'
    WHEN status_id = 4 THEN 'rejected'
    WHEN status_id = 9 THEN 'accepted'
    END AS action_type
  FROM action a 
  JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type = 'consent'
  JOIN ${SOURCE}.civicrm_activity act ON a.external_id = act.id AND a.external_system = 'civicrm_activity'
  -- BEGIN INCREMENTAL
  WHERE a.external_id > @last_id
  -- END INCREMENTAL
;

-- BEGIN INCREMENTAL
INSERT INTO growthy_campaign
  SELECT DISTINCT campaign_id
  FROM action a
  JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type = 'consent'
  JOIN ${SOURCE}.civicrm_activity act ON a.external_id = act.id AND a.external_system = 'civicrm_activity'
  WHERE (act.modified_date > a.created_at OR a.external_id > @last_id) AND act.status_id = 9
;
-- END INCREMENTAL

-- Update consents that changed their status (but are below @last_id and hence skipped)
-- BEGIN INCREMENTAL
UPDATE consent
  JOIN action
    ON consent.action_id = action.id
  JOIN ${SOURCE}.civicrm_activity a
    ON action.external_system = 'civicrm_activity' AND action.external_id = a.id
    SET consent.status = CASE
        WHEN a.status_id = 1 THEN 'pending'
        WHEN a.status_id = 4 THEN 'rejected'
        WHEN a.status_id = 9 THEN 'accepted'
                         END,
        action.created_at = a.modified_date
  WHERE a.modified_date > action.created_at
;
-- END INCREMENTAL

-- Update campaign growth
INSERT INTO campaign_metric (campaign_id, segment_id, metric, value)
  SELECT
    ap.campaign_id, @everyone, 'new_members', COUNT(DISTINCT a.contact_id)
  FROM consent c
  JOIN action a ON a.id = c.action_id
  JOIN action_page ap ON ap.id = a.action_page_id
-- BEGIN INCREMENTAL
  JOIN growthy_campaign camp ON camp.id = ap.campaign_id
-- END INCREMENTAL
  WHERE c.status = 'accepted'
  GROUP BY ap.campaign_id

  ON DUPLICATE KEY UPDATE value = VALUES(value)
;

SELECT save_last_sync_id('action', 'civicrm_activity.consent',
  (SELECT max(external_id) from action WHERE external_system = 'civicrm_activity'));


-- Update campaign action counts
INSERT INTO campaign_metric (campaign_id, segment_id, metric, value)
  SELECT
    ap.campaign_id, @everyone, 'actions', COUNT(a.id)
  FROM action a
  JOIN action_page ap ON ap.id = a.action_page_id
  WHERE ap.action_type != 'consent'
    AND a.id > @last_action
  GROUP BY ap.campaign_id

  ON DUPLICATE KEY UPDATE value = value + VALUES(value)
;

INSERT INTO campaign_metric (campaign_id, segment_id, metric, value)
  SELECT
    ap.campaign_id,
    @everyone,
    IF(ap.action_type = 'share', 'shares', 'donations') AS metric,
    COUNT(a.id)
  FROM action a
  JOIN action_page ap ON ap.id = a.action_page_id
  WHERE ap.action_type IN ('share', 'donate')
    AND a.id > @last_action
  GROUP BY ap.campaign_id, metric

  ON DUPLICATE KEY UPDATE value = value + VALUES(value)
;
