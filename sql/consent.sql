-- ORDER: 32
-- DELETE FROM consent
-- DELETE FROM campaign_metric WHERE metric IN ('new_members')

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');
SET @last_contact := (SELECT MAX(id) FROM contact);

-- BEGIN INCREMENTAL
SET @last_id := (SELECT last_sync_id('consent', 'civicrm_activity'));

CREATE TEMPORARY TABLE growthy_campaign (id INT PRIMARY KEY);
-- END INCREMENTAL


INSERT INTO consent
  (contact_id, created_at, status, trigger_action_id, campaign_id, source_id, external_id, external_system)

  SELECT
    ac.contact_id, 
    a.activity_date_time,
    CASE
    WHEN status_id = 1 THEN 'pending'
    WHEN status_id = 2 THEN 'accepted'
    WHEN status_id = 3 THEN 'cancelled'
    WHEN status_id = 4 THEN 'rejected'
    END AS status,
    t.id,
    ap.campaign_id,
    s.id,
    a.id,
    'civicrm_activity'
  FROM ${SOURCE}.civicrm_activity a
  JOIN ${SOURCE}.civicrm_activity_contact ac ON ac.activity_id = a.id AND ac.record_type_id = 2
  LEFT JOIN action t ON t.external_system='civicrm_activity' AND t.external_id = a.parent_id
  LEFT JOIN action_page ap ON ap.external_system='civicrm_campaign' AND ap.external_id=a.campaign_id
  LEFT JOIN ${SOURCE}.civicrm_value_action_source_4 utm ON utm.entity_id = a.id
  LEFT JOIN source s ON s.source = utm.source_27 COLLATE utf8_general_ci
                    AND s.medium = utm.media_28 COLLATE utf8_general_ci
                    AND s.campaign = utm.campaign_26 COLLATE utf8_general_ci
  WHERE a.activity_type_id = 68 AND ac.contact_id <= @last_contact
  -- BEGIN INCREMENTAL
    AND a.id > @last_id
  -- END INCREMENTAL
;

-- BEGIN INCREMENTAL
INSERT INTO growthy_campaign
  SELECT DISTINCT c.campaign_id
  FROM consent c
  JOIN ${SOURCE}.civicrm_activity act ON c.external_id = act.id AND c.external_system = 'civicrm_activity'
  WHERE a.external_id > @last_id AND c.status = 'accepted'
;
-- END INCREMENTAL

-- Update campaign growth
INSERT INTO campaign_metric (campaign_id, segment_id, metric, value)
  SELECT
    c.campaign_id, @everyone, 'new_members', COUNT(DISTINCT c.contact_id)
  FROM consent c
-- BEGIN INCREMENTAL
  JOIN growthy_campaign camp ON camp.id = c.campaign_id
-- END INCREMENTAL
  WHERE c.status = 'accepted' AND c.campaign_id IS NOT NULL
  GROUP BY c.campaign_id

  ON DUPLICATE KEY UPDATE value = VALUES(value)
;

SELECT save_last_sync_id('consent', 'civicrm_activity',
  (SELECT max(external_id) from consent WHERE external_system = 'civicrm_activity'));
