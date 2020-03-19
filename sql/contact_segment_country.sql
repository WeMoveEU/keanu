-- ORDER: 47
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country';
-- END INCREMENTAL

INSERT INTO contact_segment -- Country
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL
FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN ${SOURCE}.civicrm_country ctr ON s.external_id = ctr.id
JOIN contact c ON c.country = ctr.iso_code COLLATE utf8_general_ci
WHERE sn.name = 'Country'
;
