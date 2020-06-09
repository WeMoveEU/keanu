-- ORDER: 20
-- DELETE FROM source

-- ACTIVITIES --------------------------------------------------------
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT source_27, media_28, campaign_26
  FROM ${SOURCE}.civicrm_value_action_source_4
-- BEGIN INCREMENTAL
  WHERE id > last_sync_id('source', 'civicrm_value_action_source_4')
-- END INCREMENTAL
;

-- store last_id synced
SELECT save_last_sync_id('source', 'civicrm_value_action_source_4', (SELECT max(id)
                            FROM ${SOURCE}.civicrm_value_action_source_4));

-- MAILING LINKS -----------------------------------------------------------
-- for INCREMENTAL: these are append only, we could store the last id inserted and only insert new
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT
    query_param(url, 'utm_source'), query_param(url, 'utm_medium'), query_param(url, 'utm_campaign')
  FROM ${SOURCE}.civicrm_mailing_trackable_url u
  JOIN ${SOURCE}.civicrm_mailing m ON m.id=u.mailing_id
  WHERE m.scheduled_date IS NOT NULL
-- BEGIN INCREMENTAL
  AND u.id > last_sync_id('source', 'civicrm_mailing_trackable_url')
-- END INCREMENTAL
;

-- store last_id synced
SELECT save_last_sync_id('source', 'civicrm_mailing_trackable_url', (SELECT max(u.id)
                            FROM ${SOURCE}.civicrm_mailing_trackable_url u
                            JOIN ${SOURCE}.civicrm_mailing m ON m.id=u.mailing_id
                            WHERE m.scheduled_date IS NOT NULL));

-- CONTRIBUTIONS --------------------------------------------------------------
-- for INCREMENTAL: these are append only, we could store the last id inserted and only insert new
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT utm_source_30, utm_medium_31, utm_campaign_33
  FROM ${SOURCE}.civicrm_value_utm_5
-- BEGIN INCREMENTAL
  WHERE id > last_sync_id('source', 'civicrm_value_utm_5')
-- END INCREMENTAL
;

-- store last id synced
SELECT save_last_sync_id('source', 'civicrm_value_utm_5', (SELECT max(id) FROM ${SOURCE}.civicrm_value_utm_5));

-- RECURRING CONTRIBUTIONS --------------------------------------------
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT utm_source, utm_medium, utm_campaign
  FROM ${SOURCE}.civicrm_value_recur_utm
  -- BEGIN INCREMENTAL
  WHERE id > last_sync_id('source', 'civicrm_value_recur_utm')
  -- END INCREMENTAL
;

-- store last_id synced
SELECT save_last_sync_id('source', 'civicrm_value_recur_utm', (SELECT max(id) FROM ${SOURCE}.civicrm_value_recur_utm));

