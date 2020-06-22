-- ORDER: 47
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'

SET @query_start := NOW();

SET @max_modified_date := (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact); 
SET @last_update_dt := (SELECT last_sync_dt('contact_segment.country', 'civicrm_contact'));


INSERT INTO contact_segment -- Country
  (segmentation_id, segment_id, contact_id, joined_at, left_at)

  SELECT
    s.segmentation_id, s.id, c.id, c.created_at, NULL
  FROM segmentation sn
  JOIN segment s ON s.segmentation_id = sn.id
  JOIN contact c ON c.country = s.name
-- BEGIN INCREMENTAL
  JOIN ${SOURCE}.civicrm_contact civi_c ON c.id = civi_c.id AND civi_c.modified_date > @last_update_dt
-- END INCREMENTAL
  WHERE sn.name = 'Country'
-- BEGIN INCREMENTAL
  ON DUPLICATE KEY UPDATE segment_id=VALUES(segment_id)
-- END INCREMENTAL
;

SELECT save_last_sync_dt('contact_segment.country', 'civicrm_contact', @max_modified_date);
SELECT save_last_sync_dt('contact_segment_country', 'query_start', @query_start);
