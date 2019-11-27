-- ORDER: 20
-- DELETE FROM source

-- Activities
INSERT IGNORE INTO source (campaign, source, medium)
  SELECT campaign_26, source_27, media_28
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
