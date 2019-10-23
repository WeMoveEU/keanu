-- Use this view to figure out which campaign id is assigned to a Civi CONTRIB RECUR id
DROP VIEW IF EXISTS contribution_recur_to_campaign;

CREATE VIEW contribution_recur_to_campaign AS
  SELECT
    rd.id,
    CASE
      WHEN c.id IS NULL THEN
       CASE
        WHEN utm.utm_medium = 'drupal-survey' THEN
         (SELECT id from campaign where name = 'Survey Fundraising')
        ELSE
         (SELECT id from campaign where name = 'Unknown Fundraising')
       END
      ELSE c.id
    END as campaign_id,
    m.id as mailing_id,
    utm.utm_source,
    utm.utm_medium,
    utm.utm_campaign

  -- useful join for getting campaign by the utm-mailing

  FROM wemove_47.civicrm_contribution_recur rd
  LEFT JOIN wemove_47.civicrm_value_recur_utm utm
    ON utm.entity_id = rd.id
  LEFT JOIN wemove_47.civicrm_mailing m
    ON (utm.utm_medium = 'email' AND SUBSTRING(utm.utm_source, 10) = m.id)
  LEFT JOIN wemove_47.civicrm_campaign c_speakout
    ON (utm.utm_medium = 'speakout' AND SUBSTRING(utm.utm_source, 10) = c_speakout.external_identifier)
  LEFT JOIN campaign c
    ON c.external_id = COALESCE(m.campaign_id, c_speakout.id)

  WHERE rd.is_test = 0
;
