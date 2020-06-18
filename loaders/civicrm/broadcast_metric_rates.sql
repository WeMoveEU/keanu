-- ORDER: 57
-- DELETE FROM broadcast_metric WHERE metric IN ('openers_rate', 'clickers_rate', 'clickers_to_openers', 'converted_to_clickers', 'sharers_rate', 'likely_forwarders_rate', 'bounce_rate', 'spam_rate')

SET @query_start := NOW();

SET @everyone = (SELECT id FROM segment WHERE name = 'Everyone');

CREATE TEMPORARY TABLE bm_segment AS
  SELECT @everyone AS id
  UNION
  SELECT s.id from segment s JOIN segmentation sn ON sn.id = s.segmentation_id
  WHERE sn.name = 'Country';

CREATE INDEX bm_segment_id ON bm_segment (id);
-- Country breakdown also for metrics:
-- openers_rate - depends on: openers (open.sql) and recipients (broadcast_metric.sql)
-- clickers_to_openers - depends on: clickers (click.sql) and openers
-- converted_to_clickers - depends on: converted (broadcast_metric.sql) and clickers

INSERT INTO broadcast_metric -- openers_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'openers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'openers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;

INSERT INTO broadcast_metric -- clickers_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'clickers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'clickers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;

INSERT INTO broadcast_metric -- unsub_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
  SELECT
    b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'unsub_rate',
    b1.value / b2.value
  FROM broadcast_metric b1
  JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
   AND b1.metric = 'unsubs' AND b2.metric = 'recipients' AND b1.segment_id = b2.segment_id

  ON DUPLICATE KEY UPDATE value=VALUES(value)
;

INSERT INTO broadcast_metric -- clickers_to_openers
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'clickers_to_openers',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'clickers' AND b2.metric = 'openers'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;

INSERT INTO broadcast_metric -- converted_to_clickers
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'converted_to_clickers',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'converted' AND b2.metric = 'clickers'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;


INSERT INTO broadcast_metric -- sharers_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'sharers_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'sharers' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;


INSERT INTO broadcast_metric -- likely_forwarders_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'likely_forwarders_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'likely_forwarders' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;


INSERT INTO broadcast_metric -- bounce_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'bounce_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'bounces' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;

INSERT INTO broadcast_metric -- spam_rate
            (broadcast_id, broadcast_name, segment_id, metric, value)
SELECT
  b1.broadcast_id, b1.broadcast_name, b1.segment_id, 'spam_rate',
  b1.value / b2.value
  FROM broadcast_metric b1
         JOIN broadcast_metric b2 ON b1.broadcast_id = b2.broadcast_id
             AND b1.metric = 'spams' AND b2.metric = 'recipients'
             AND b1.segment_id = b2.segment_id
             ON DUPLICATE KEY UPDATE value=VALUES(value)
         ;

DROP TABLE bm_segment;

SELECT save_last_sync_dt('broadcast_metric_rates', 'query_start', @query_start);
