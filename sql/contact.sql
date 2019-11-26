-- ORDER: 5
-- DELETE FROM contact
-- From WM CiviCRM
-- We base it on:
-- civicrm_contact

INSERT INTO contact
  (
    id,
   email_domain,
   created_at,
   postal_code,
   country,
   preferred_language,
   latitude, longitude
  )

  SELECT
    c.id,
    MIN(substring(e.email FROM locate('@', e.email) + 1)),
    COALESCE(c.created_date, c.modified_date),
    substr(MIN(a.postal_code), 1, 10),
    lower(MIN(ctr.iso_code)),
    c.preferred_language,
    MIN(a.geo_code_1), MIN(a.geo_code_2)

  FROM ${SOURCE}.civicrm_contact c 
  LEFT JOIN ${SOURCE}.civicrm_email e ON e.contact_id = c.id AND e.is_primary
  LEFT JOIN ${SOURCE}.civicrm_address a ON a.contact_id = c.id AND a.is_primary
  LEFT JOIN ${SOURCE}.civicrm_country ctr ON ctr.id = a.country_id

  WHERE NOT c.is_deleted
-- BEGIN INCREMENTAL
  AND c.id NOT IN (SELECT id FROM contact)
-- END INCREMENTAL

  GROUP BY c.id
;
