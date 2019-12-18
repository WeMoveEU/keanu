-- ORDER: 63
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.external_system = 'civicrm_option_group'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.external_system = 'civicrm_option_group';
-- END INCREMENTAL

INSERT INTO contact_segment -- Preferred Language
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL
FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN ${SOURCE}.civicrm_option_value ov ON s.external_id = ov.id
JOIN contact c ON SUBSTRING(c.preferred_language, 1, 2) = ov.value COLLATE utf8_general_ci
WHERE sn.name = 'Preferred language';


INSERT INTO contact_segment -- Active and Donor status
(segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT
s.segmentation_id, s.id,
c.id, c.created_at, NULL
FROM
segmentation sn JOIN segment s ON s.segmentation_id = sn.id
JOIN ${SOURCE}.civicrm_option_value ov ON s.external_id = ov.id
JOIN ${SOURCE}.civicrm_value_contact_segments vcs ON
     CASE WHEN sn.name = 'Recurring donors' THEN vcs.recurring_donor = ov.value
          WHEN sn.name = 'Active status' THEN vcs.active_status = ov.value
     END
JOIN contact c ON vcs.entity_id = c.id
WHERE sn.name in ('Recurring donors', 'Active status');

