-- ORDER: 52
-- DELETE FROM broadcast_link

INSERT INTO broadcast_link (broadcast_id, url, source_id, external_system, external_id)
  SELECT
    b.id, u.url, s.id, 'civicrm_mailing_trackable_url', u.id
  FROM ${SOURCE}.civicrm_mailing_trackable_url u
  JOIN ${SOURCE}.civicrm_mailing m ON m.id=u.mailing_id
  JOIN broadcast b ON b.external_system='civicrm_mailing' AND b.external_id=u.mailing_id
  JOIN source s ON s.source=query_param(u.url, 'utm_source')
                AND s.medium=query_param(u.url, 'utm_medium')
                AND s.campaign=query_param(u.url, 'utm_campaign')
  WHERE m.scheduled_date IS NOT NULL
-- BEGIN INCREMENTAL
  AND u.id NOT IN (SELECT external_id FROM broadcast_link WHERE external_system = 'civicrm_mailing_trackable_url')
-- END INCREMENTAL
;
