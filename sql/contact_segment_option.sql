-- ORDER: 66
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.external_system = 'civicrm_option_group' AND sn.name != 'Active status'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs
          JOIN segment s ON cs.segment_id = s.id
          JOIN segmentation sn ON sn.id = s.segmentation_id
          JOIN hot_contact hc ON cs.contact_id = hc.id AND hc.modified
          WHERE sn.external_system = 'civicrm_option_group' AND sn.name = 'Preferred language';
-- END INCREMENTAL

INSERT INTO contact_segment -- Preferred Language
  (segmentation_id, segment_id, contact_id, joined_at, left_at)
  SELECT
    s.segmentation_id, s.id, c.id, c.created_at, NULL
  FROM segmentation sn
  JOIN segment s ON s.segmentation_id = sn.id
  JOIN ${SOURCE}.civicrm_option_value ov ON s.external_id = ov.id
  JOIN contact c ON SUBSTRING(c.preferred_language, 1, 2) = ov.value COLLATE utf8_general_ci
-- BEGIN INCREMENTAL
   JOIN hot_contact hc ON c.id = hc.id AND hc.modified
-- END INCREMENTAL
  WHERE sn.name = 'Preferred language'
;

