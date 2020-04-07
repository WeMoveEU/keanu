-- ORDER: 67
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'

SET @max_modified_date := (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact); 
SET @last_update_dt := (SELECT last_sync_dt('contact_segment.country', 'civicrm_contact'));


INSERT INTO contact_segment -- Country
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL
FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN ${SOURCE}.civicrm_country ctr ON s.external_id = ctr.id
JOIN ${SOURCE}.civicrm_contact c ON c.country = ctr.iso_code COLLATE utf8_general_ci
 WHERE sn.name = 'Country'
  -- BEGIN INCREMENTAL
  AND c.modified_date > @last_update_dt
  -- END INCREMENTAL

ON DUPLICATE KEY UPDATE segment_id = s.id
;


SELECT save_last_sync_dt('contact_segment.country', 'civicrm_contact',
                         (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact));
