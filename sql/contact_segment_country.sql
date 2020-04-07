-- ORDER: 47
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'

SET @max_modified_date := (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact); 
SET @last_update_dt := (SELECT last_sync_dt('contact_segment.country', 'civicrm_contact'));


INSERT INTO contact_segment -- Country
  (segmentation_id, segment_id, contact_id, joined_at, left_at)

  SELECT
    s.segmentation_id, s.id, c.id, c.created_at, NULL
  FROM segmentation sn
  JOIN segment s ON s.segmentation_id = sn.id
  JOIN contact c ON c.country = s.name
  WHERE sn.name = 'Country'
;


SELECT save_last_sync_dt('contact_segment.country', 'civicrm_contact',
                         (SELECT max(modified_date) FROM ${SOURCE}.civicrm_contact));
