-- PREFERENCE: 5
-- ID_MAPS_TO: CIVICRM
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

  FROM wemove_47.civicrm_contact c 
  LEFT JOIN wemove_47.civicrm_email e ON e.contact_id = c.id AND e.is_primary
  LEFT JOIN wemove_47.civicrm_address a ON a.contact_id = c.id AND a.is_primary
  LEFT JOIN wemove_47.civicrm_country ctr ON ctr.id = a.country_id

  WHERE c.contact_type = 'Individual'
  AND NOT c.is_deleted

  GROUP BY c.id
;
