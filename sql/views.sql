-- ORDER: 4
-- Use this view to figure out which campaign id is assigned to a Civi CONTRIB RECUR id
DROP VIEW IF EXISTS contribution_recur_to_campaign;

CREATE VIEW contribution_recur_to_campaign AS
  SELECT
    rd.id,
    m.id as mailing_id,
    language_4 as language,
    utm.utm_source,
    utm.utm_medium,
    utm.utm_campaign

  -- useful join for getting campaign by the utm-mailing

  FROM ${SOURCE}.civicrm_contribution_recur rd
  LEFT JOIN ${SOURCE}.civicrm_value_recur_utm utm
    ON utm.entity_id = rd.id
  LEFT JOIN ${SOURCE}.civicrm_mailing m
    ON (utm.utm_medium = 'email' AND SUBSTRING(utm.utm_source, 10) = m.id)
  LEFT JOIN ${SOURCE}.civicrm_campaign c_speakout
    ON (utm.utm_medium = 'speakout' AND SUBSTRING(utm.utm_source, 10) = c_speakout.external_identifier)
  LEFT JOIN campaign c
    ON c.external_id = COALESCE(m.campaign_id, c_speakout.id)
  LEFT JOIN ${SOURCE}.civicrm_value_speakout_integration_2 xc
    ON xc.entity_id = COALESCE(m.campaign_id, c_speakout.id)

  WHERE rd.is_test = 0
;

-- Broadcast info and main metrics displayed in broadcast lists
DROP VIEW IF EXISTS broadcast_summary;

CREATE VIEW broadcast_summary AS
  SELECT
    b.id, b.name, b.ask_type, b.language, b.broadcast_test_id, b.sent_at, b.campaign_id,
    r.segment_id,
    r.value AS recipients,
    o.value AS openers,
    c.value AS clickers,
    u.value AS unsubs,
    a.value AS converted,
    f.value AS likely_forwarders
  FROM broadcast b
  JOIN broadcast_metric r ON r.broadcast_id = b.id AND r.metric = 'recipients'
  JOIN broadcast_metric o ON o.broadcast_id = b.id AND o.segment_id = r.segment_id AND o.metric = 'openers'
  JOIN broadcast_metric c ON c.broadcast_id = b.id AND c.segment_id = r.segment_id AND c.metric = 'clickers'
  JOIN broadcast_metric u ON u.broadcast_id = b.id AND u.segment_id = r.segment_id AND u.metric = 'unsubs'
  JOIN broadcast_metric a ON a.broadcast_id = b.id AND a.segment_id = r.segment_id AND a.metric = 'converted'
  JOIN broadcast_metric f ON f.broadcast_id = b.id AND f.segment_id = r.segment_id AND f.metric = 'likely_forwarders'
;
