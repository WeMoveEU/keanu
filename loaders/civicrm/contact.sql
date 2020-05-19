-- ORDER: 5
-- DELETE FROM contact
-- From WM CiviCRM
-- We base it on:
-- civicrm_contact

-- BEGIN INCREMENTAL
SET @last_contact := (SELECT MAX(id) FROM contact);
-- END INCREMENTAL

DROP VIEW IF EXISTS civicrm_contact_to_contact;
CREATE VIEW civicrm_contact_to_contact AS
SELECT
  c.id,
  MIN(SUBSTRING(e.email FROM LOCATE('@', e.email) + 1)) as email_domain,
  COALESCE(c.created_date, c.modified_date) as created_at,
  SUBSTR(MIN(a.postal_code), 1, 10) as postal_code,
  substring_index(ctr.name, ',', 1) as country, -- strip "X, republic of", etc.
  c.preferred_language,
  MIN(a.geo_code_1) as latitude,
  MIN(a.geo_code_2) as longitude
FROM ${SOURCE}.civicrm_contact c 
LEFT JOIN ${SOURCE}.civicrm_email e ON e.contact_id = c.id AND e.is_primary
LEFT JOIN ${SOURCE}.civicrm_address a ON a.contact_id = c.id AND a.is_primary
LEFT JOIN ${SOURCE}.civicrm_country ctr ON ctr.id = a.country_id

GROUP BY c.id, country
;


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
SELECT *
FROM civicrm_contact_to_contact c
-- BEGIN INCREMENTAL
  WHERE c.id > @last_contact
-- END INCREMENTAL
;

SET @max_modified_dt := (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact); 
-- BEGIN INCREMENTAl
SET @last_update_dt := (SELECT last_sync_dt('contact', 'civicrm_contact'));

UPDATE contact dc
JOIN ${SOURCE}.civicrm_contact cc ON dc.id = cc.id AND cc.modified_date > @last_update_dt
JOIN civicrm_contact_to_contact sc ON dc.id = sc.id
SET
 dc.email_domain = sc.email_domain,
 dc.postal_code = sc.postal_code,
 dc.country = sc.country,
 dc.preferred_language = sc.preferred_language,
 dc.latitude = sc.latitude,
 dc.longitude = sc.longitude
;
-- END INCREMENTAL


-- Use MIN(created_date, MIN(activity_date_time)) as contact creation date,
-- as a contact record may be created much later than the first activity date, in some ciscurmstances.
-- This is done in a separate query to limit the size of the overall JOIN
UPDATE contact c
  JOIN (
    SELECT contact_id, MIN(activity_date_time) AS date_time
      FROM ${SOURCE}.civicrm_activity_contact ac
      JOIN ${SOURCE}.civicrm_activity a ON a.id = ac.activity_id AND ac.record_type_id = 2
-- BEGIN INCREMENTAL
      WHERE contact_id > @last_contact
-- END INCREMENTAL
      GROUP BY contact_id
  ) min_act ON min_act.contact_id = c.id
  SET c.created_at = min_act.date_time
  WHERE c.created_at > min_act.date_time
-- BEGIN INCREMENTAL
    AND c.id > @last_contact
-- END INCREMENTAL
;

DROP VIEW IF EXISTS civicrm_contact_to_contact;

SELECT save_last_sync_dt('contact', 'civicrm_contact', @max_modified_dt);
