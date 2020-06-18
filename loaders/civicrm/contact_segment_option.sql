-- ORDER: 46
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.external_system = 'civicrm_option_group' AND sn.name != 'Active status'

SET @query_start := NOW();

-- BEGIN INCREMENTAL
SET @last_update_dt := (SELECT last_sync_dt('contact.preferred_language', 'civicrm_option_value'));

CREATE TEMPORARY TABLE updated
SELECT id FROM ${SOURCE}.civicrm_contact
WHERE modified_date > @last_update_dt;

CREATE INDEX update_ids ON updated (id);

DELETE cs
FROM contact_segment cs
JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id
JOIN updated ON updated.id = cs.contact_id
WHERE sn.external_system = 'civicrm_option_group' AND sn.name = 'Preferred language'
;
-- END INCREMENTAL

INSERT INTO contact_segment -- Preferred Language
  (segmentation_id, segment_id, contact_id, joined_at, left_at)
  SELECT
    s.segmentation_id, s.id, c.id, c.created_at, NULL
  FROM segmentation sn
  JOIN segment s ON s.segmentation_id = sn.id
  JOIN ${SOURCE}.civicrm_option_value ov ON s.external_id = ov.id
  JOIN contact c ON c.preferred_language = ov.name COLLATE utf8_general_ci
  WHERE sn.name = 'Preferred language'
-- BEGIN INCREMENTAL
  AND
  c.id IN (SELECT id FROM updated)
-- END INCREMENTAL
;

SELECT save_last_sync_dt('contact.preferred_language', 'civicrm_option_value',
       (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact));

SELECT save_last_sync_dt('contact_segment_option', 'query_start', @query_start);
