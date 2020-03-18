-- ORDER: 58
-- DELETE FROM broadcast_metric WHERE metric IN ('activated', 'activated_rate')

-- Country breakdown also for metrics:
-- activated_rate - depends on: activated

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


INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'activated_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'activated' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;
