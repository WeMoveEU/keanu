-- ORDER: 64
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Active status'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Active status';
-- END INCREMENTAL

CREATE TEMPORARY TABLE event_history (
  contact_id INT UNSIGNED NOT NULL,
  create_date DATETIME NOT NULL,
  event_type ENUM('0_join', '1_leave', '2_action', '3_expiry'),
  event_date DATETIME,
  action_id INT UNSIGNED,
  INDEX order_idx (contact_id, event_date, event_type)
);

SET @segid := (SELECT id FROM segment WHERE name = 'Member');

INSERT INTO event_history
  SELECT
    contact_id,
    c.created_at,
    '0_join',
    joined_at,
    NULL
  FROM contact c
  JOIN contact_segment cs ON cs.contact_id = c.id AND segment_id = @segid
;

INSERT INTO event_history
  SELECT
    contact_id,
    c.created_at,
    '1_leave',
    left_at,
    NULL
  FROM contact c
  JOIN contact_segment cs ON cs.contact_id = c.id AND segment_id = @segid
  WHERE left_at IS NOT NULL
;

INSERT INTO event_history
  SELECT
    c.id AS contact_id, 
    c.created_at,
    '2_action',
    a.created_at AS event_date,
    a.id
  FROM contact c 
  LEFT JOIN action a ON a.contact_id = c.id
  LEFT JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type != 'consent'
;

INSERT INTO event_history
  SELECT
    c.id AS contact_id, 
    c.created_at,
    '3_expiry',
    DATE_ADD(a.created_at, INTERVAL 3 MONTH),
    NULL
  FROM contact c
  JOIN action a ON a.contact_id = c.id AND a.created_at < DATE_SUB(NOW(), INTERVAL 3 MONTH)
  JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type != 'consent'
  LEFT JOIN action oa ON oa.contact_id = c.id 
                      AND oa.created_at > a.created_at 
                      AND oa.created_at < DATE_ADD(a.created_at, INTERVAL 3 MONTH)
  WHERE oa.id IS NULL
;

DROP TABLE IF exists segment_history;
CREATE TABLE segment_history (
  contact_id INT UNSIGNED NOT NULL,
  event_date DATETIME,
  trigger_action_id INT UNSIGNED,
  is_member TINYINT NOT NULL,
  leaved INT UNSIGNED REFERENCES segment(id),
  joined INT UNSIGNED NOT NULL REFERENCES segment(id),
  last_action DATETIME,
  prev_contact INT UNSIGNED NOT NULL,
  INDEX (contact_id, event_date)
);

SET @active_status := (SELECT id FROM segmentation WHERE name = 'Active status');
SET @notmember := (SELECT id FROM segment WHERE name = 'Not_a_member');
SET @inactive := (SELECT id FROM segment WHERE name = 'Inactive');
SET @active := (SELECT id FROM segment WHERE name = 'Active');

SELECT @prev_contact := NULL, @is_member := 0, @last_action := NULL, @joined := @notmember;
INSERT INTO segment_history
  SELECT
    contact_id,
    COALESCE(event_date, create_date),
    action_id,

    @is_member := CASE
      WHEN event_type = '0_join' THEN 1
      WHEN event_type = '1_leave' THEN 0
      WHEN @prev_contact != contact_id THEN 0
      ELSE @is_member
    END,

    IF (@prev_contact != contact_id, NULL, @joined),

    @joined := CASE
      WHEN event_type = '0_join' THEN @inactive
      WHEN event_type = '1_leave' THEN @notmember
      WHEN event_type = '2_action' 
        AND @is_member
        AND event_date >= DATE_ADD(create_date, INTERVAL 1 DAY)
        THEN @active
      WHEN event_type = '2_action' THEN IF(@is_member, @inactive, @notmember)
      WHEN event_type = '3_expiry' AND @joined = @active THEN @inactive
      ELSE @joined
    END,

    @last_action := CASE
      WHEN @prev_contact != contact_id THEN NULL
      WHEN event_type = '2_action' THEN event_date
      ELSE @last_action
    END,

    @prev_contact := contact_id

  FROM event_history
  ORDER BY contact_id, event_date, event_type
;

INSERT INTO contact_segment
  (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id)

  SELECT 
    s.segmentation_id, s.id, j.contact_id, j.event_date, MIN(l.event_date), j.trigger_action_id
  FROM segment s
  JOIN segment_history j ON j.joined = s.id AND (j.leaved IS NULL OR j.leaved != j.joined)
  LEFT JOIN segment_history l ON l.leaved = s.id AND l.contact_id = j.contact_id AND l.leaved != l.joined AND l.event_date >= j.event_date
  WHERE s.segmentation_id = @active_status
  GROUP BY s.id, j.contact_id, j.event_date, j.trigger_action_id
;

DROP TABLE event_history;
DROP TABLE segment_history;
