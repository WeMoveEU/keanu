-- ORDER: 80
-- DELETE FROM broadcast_metric WHERE metric IN ('activated')

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');
SET @active = (SELECT id FROM segment WHERE name = 'Active');

INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b.id, b.name, @Everyone, 'activated', COUNT(DISTINCT a.contact_id)
  FROM action a
  JOIN contact_segment cs ON cs.trigger_action_id = a.id AND cs.segment_id = @active
  JOIN broadcast_link l ON l.source_id = a.source_id
  JOIN broadcast b ON b.id = l.broadcast_id
  GROUP BY b.id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;
