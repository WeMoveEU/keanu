-- ORDER: 32
-- DELETE FROM share

INSERT INTO share (action_id, conversion_count, share_count, new_member_count)
  SELECT
    a.id,
    COALESCE(SUM(ap.action_type IN ('call', 'email', 'sign', 'tweet', 'facebook')), 0),
    COALESCE(SUM(ap.action_type = 'share'), 0),
    0
  FROM ${SOURCE}.civicrm_value_share_params_6 sh
  JOIN action a ON sh.entity_id = a.external_id AND a.external_system = 'civicrm_activity'
  LEFT JOIN source s ON s.source = sh.utm_source_37 COLLATE utf8_general_ci
                    AND s.medium = sh.utm_medium_38 COLLATE utf8_general_ci
                    AND s.campaign = sh.utm_campaign_39 COLLATE utf8_general_ci
  LEFT JOIN action v ON v.source_id = s.id
  LEFT JOIN action_page ap ON v.action_page_id = ap.id
  GROUP BY a.id
;

