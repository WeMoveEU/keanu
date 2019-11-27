-- ORDER: 20
-- DELETE FROM source
INSERT IGNORE INTO source (campaign, source, medium)
  SELECT campaign_26, source_27, media_28
  FROM ${SOURCE}.civicrm_value_action_source_4
;
