-- ORDER: 57
-- DELETE FROM broadcast_metric WHERE metric IN ('openers_rate', 'clickers_rate', 'sharers_rate', 'likely_forwarders_rate')


INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'openers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'openers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;



INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'clickers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'clickers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;


INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'sharers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'sharers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;


INSERT INTO broadcast_metric (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'likely_forwarders_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'likely_forwarders' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;
