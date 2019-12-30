-- ORDER: 32
-- DELETE FROM share

-- BEGIN INCREMENTAL
DELETE FROM share;
-- END INCREMENTAL

INSERT INTO share (action_id, shared_source_id, conversion_count, share_count, new_member_count)
  SELECT
    a.id, utm.id, 0, 0, 0
  FROM ${SOURCE}.civicrm_value_share_params_6 sh
  JOIN action a ON sh.entity_id = a.external_id AND a.external_system = 'civicrm_activity'
  LEFT JOIN source utm ON utm.source = sh.utm_source_37 COLLATE utf8_general_ci
                       AND utm.medium = sh.utm_medium_38 COLLATE utf8_general_ci
                       AND utm.campaign = sh.utm_campaign_39 COLLATE utf8_general_ci
;

UPDATE share sh JOIN (
    SELECT utm.id AS source_id, COUNT(DISTINCT v.contact_id) AS converted
    FROM source utm
    JOIN action v ON v.source_id = utm.id
    JOIN action_page ap ON v.action_page_id = ap.id
                        AND ap.action_type IN ('call', 'email', 'sign', 'tweet', 'facebook')
    GROUP BY source_id
  ) tmp ON tmp.source_id = sh.shared_source_id
  SET sh.conversion_count = tmp.converted
;

UPDATE share sh JOIN (
    SELECT utm.id AS source_id, COUNT(DISTINCT v.contact_id) AS converted
    FROM source utm
    JOIN action v ON v.source_id = utm.id
    JOIN action_page ap ON v.action_page_id = ap.id AND ap.action_type = 'share'
    GROUP BY source_id
  ) tmp ON tmp.source_id = sh.shared_source_id
  SET sh.share_count = tmp.converted
;

UPDATE share sh JOIN (
    SELECT utm.id AS source_id, COUNT(DISTINCT v.contact_id) AS converted
    FROM source utm
    JOIN action v ON v.source_id = utm.id
    JOIN action_page ap ON v.action_page_id = ap.id AND ap.action_type = 'consent'
    JOIN consent c ON c.action_id = v.id AND c.status = 'accepted'
    GROUP BY source_id
  ) tmp ON tmp.source_id = sh.shared_source_id
  SET sh.new_member_count = tmp.converted
;
