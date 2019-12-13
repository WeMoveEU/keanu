-- ORDER: 63
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Everyone'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Everyone';
-- BEGIN INCREMENTAL

INSERT INTO contact_segment -- Everyone 
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL

FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN contact c
WHERE sn.name = 'Everyone' AND s.name = 'Everyone';

