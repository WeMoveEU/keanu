-- ORDER: 67
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs
          JOIN segment s ON cs.segment_id = s.id
          JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Country'
          JOIN hot_contact hc ON cs.contact_id = hc.id AND hc.modified
;
-- END INCREMENTAL

INSERT INTO contact_segment -- Country
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL
FROM
contact c
-- BEGIN INCREMENTAL
JOIN hot_contact hc ON cs.contact_id = hc.id AND hc.modified
-- END INCREMENTAL
JOIN ${SOURCE}.civicrm_country ctr ON c.country = ctr.iso_code COLLATE utf8_general_ci

JOIN segment s ON ${SOURCE}.civicrm_country ctr ON s.external_id = ctr.id
JOIN segmentation sn ON s.segmentation_id = sn.id AND sn.name = 'Country'
;
