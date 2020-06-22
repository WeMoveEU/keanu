-- ORDER: 43
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Everyone'

SET @query_start := NOW();

SET @last_sync_id := (SELECT last_sync_id('contact_segment.everyone', 'contact'));
SET @max_contact_id := (SELECT max(id) from contact);

INSERT INTO contact_segment -- Everyone
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL

FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN contact c
WHERE sn.name = 'Everyone' AND s.name = 'Everyone' AND c.id > @last_sync_id;

SELECT save_last_sync_id('contact_segment.everyone', 'contact', @max_contact_id);
SELECT save_last_sync_dt('contact_segment_everyone', 'query_start', @query_start);
