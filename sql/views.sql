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
  LEFT JOIN broadcast_metric r ON r.broadcast_id = b.id AND r.metric = 'recipients'
  LEFT JOIN broadcast_metric o ON o.broadcast_id = b.id AND o.segment_id = r.segment_id AND o.metric = 'openers'
  LEFT JOIN broadcast_metric c ON c.broadcast_id = b.id AND c.segment_id = r.segment_id AND c.metric = 'clickers'
  LEFT JOIN broadcast_metric u ON u.broadcast_id = b.id AND u.segment_id = r.segment_id AND u.metric = 'unsubs'
  LEFT JOIN broadcast_metric a ON a.broadcast_id = b.id AND a.segment_id = r.segment_id AND a.metric = 'converted'
  LEFT JOIN broadcast_metric f ON f.broadcast_id = b.id AND f.segment_id = r.segment_id AND f.metric = 'likely_forwarders'
;


-- Campaign info and main metrics displayed in campaign lists
DROP VIEW IF EXISTS campaign_summary;

CREATE VIEW campaign_summary AS
  SELECT
    c.id, c.name, c.campaign_type, c.started_at, c.ended_at,
    m.segment_id,
    m.value AS messages,
    a.value AS actions,
    s.value AS shares,
    n.value AS new_members,
    u.value AS unsubs,
    aed.value AS activated,
    d.value AS donations,
    dta.value AS donations_total_amount
  FROM campaign c
  LEFT JOIN campaign_metric m   ON m.campaign_id   = c.id AND m.metric = 'messages'
  LEFT JOIN campaign_metric a   ON a.campaign_id   = c.id AND a.segment_id   = m.segment_id AND a.metric = 'actions'
  LEFT JOIN campaign_metric s   ON s.campaign_id   = c.id AND s.segment_id   = m.segment_id AND s.metric = 'shares'
  LEFT JOIN campaign_metric n   ON n.campaign_id   = c.id AND n.segment_id   = m.segment_id AND n.metric = 'new_members'
  LEFT JOIN campaign_metric u   ON u.campaign_id   = c.id AND u.segment_id   = m.segment_id AND u.metric = 'unsubs'
  LEFT JOIN campaign_metric aed ON aed.campaign_id = c.id AND aed.segment_id = m.segment_id AND aed.metric = 'activated'
  LEFT JOIN campaign_metric d   ON d.campaign_id   = c.id AND d.segment_id   = m.segment_id AND d.metric = 'donations'
  LEFT JOIN campaign_metric dta ON dta.campaign_id = c.id AND dta.segment_id = m.segment_id AND dta.metric = 'donations_total_amount'
;
