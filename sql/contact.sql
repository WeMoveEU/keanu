-- ORDER: 5
-- DELETE FROM contact
-- From WM CiviCRM
-- We base it on:
-- civicrm_contact

-- BEGIN INCREMENTAL
SET @last_contact = (SELECT MAX(id) FROM contact);
-- END INCREMENTAL

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
    MIN(SUBSTRING(e.email FROM LOCATE('@', e.email) + 1)),
    COALESCE(c.created_date, c.modified_date),
    SUBSTR(MIN(a.postal_code), 1, 10),
    LOWER(MIN(ctr.iso_code)),
    c.preferred_language,
    MIN(a.geo_code_1), MIN(a.geo_code_2)

  FROM ${SOURCE}.civicrm_contact c 
  LEFT JOIN ${SOURCE}.civicrm_email e ON e.contact_id = c.id AND e.is_primary
  LEFT JOIN ${SOURCE}.civicrm_address a ON a.contact_id = c.id AND a.is_primary
  LEFT JOIN ${SOURCE}.civicrm_country ctr ON ctr.id = a.country_id

-- BEGIN INCREMENTAL
  WHERE c.id > @last_contact
-- END INCREMENTAL

  GROUP BY c.id
;

-- Use MIN(created_date, MIN(activity_date_time)) as contact creation date,
-- as a contact record may be created much later than the first activity date, in some ciscurmstances.
-- This is done in a separate query to limit the size of the overall JOIN
UPDATE contact c
  JOIN (
    SELECT contact_id, MIN(activity_date_time) AS date_time
      FROM ${SOURCE}.civicrm_activity_contact ac
      JOIN ${SOURCE}.civicrm_activity a ON a.id = ac.activity_id AND ac.record_type_id = 2
      GROUP BY contact_id
  ) min_act ON min_act.contact_id = c.id
  SET c.created_at = min_act.date_time
  WHERE c.created_at > min_act.date_time
-- BEGIN INCREMENTAL
    AND c.id > @last_contact
-- END INCREMENTAL
;
