-- ORDER: 1
-- DELETE FROM source
INSERT IGNORE INTO source (campaign, source, medium)
  SELECT campaign_26, source_27, media_28
  FROM wemove_47.civicrm_value_action_source_4
;

INSERT IGNORE INTO source (source, medium, campaign)
SELECT utm_source_30, utm_medium_31, utm_campaign_33
FROM wemove_47.civicrm_value_utm_5
;

INSERT IGNORE INTO source (source, medium, campaign)
SELECT utm_source, utm_medium, utm_campaign
FROM wemove_47.civicrm_value_recur_utm
;
