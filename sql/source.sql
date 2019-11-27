-- ORDER: 20
-- DELETE FROM source

-- Activities
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT source_27, media_28, campaign_26
  FROM ${SOURCE}.civicrm_value_action_source_4
;

-- Mailing links
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT
    query_param(url, 'utm_source'), query_param(url, 'utm_medium'), query_param(url, 'utm_campaign')
  FROM ${SOURCE}.civicrm_mailing_trackable_url u
  JOIN ${SOURCE}.civicrm_mailing m ON m.id=u.mailing_id
  WHERE m.scheduled_date IS NOT NULL
;

-- Contributions
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT utm_source_30, utm_medium_31, utm_campaign_33
  FROM ${SOURCE}.civicrm_value_utm_5
;

-- Recurring contributions
INSERT IGNORE INTO source (source, medium, campaign)
  SELECT utm_source, utm_medium, utm_campaign
  FROM ${SOURCE}.civicrm_value_recur_utm
;