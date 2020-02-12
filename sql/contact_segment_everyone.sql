-- ORDER: 63
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Everyone'

-- BEGIN INCREMENTAL
SET @last_sync_id := (SELECT last_sync_id('contact_segment.everyone', 'contact'));
-- END INCREMENTAL

INSERT INTO contact_segment -- Everyone 
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL

FROM segmentation sn
JOIN segment s ON s.segmentation_id = sn.id
JOIN contact c
WHERE
      sn.name = 'Everyone' AND s.name = 'Everyone'
-- BEGIN INCREMENTAL
  AND c.id > @last_sync_id
-- END INCREMENTAL
;


SELECT save_last_sync_id('contact_segment.everyone', 'contact',
       (SELECT max(id) FROM contact));
