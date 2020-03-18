-- ORDER: 45
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Recurring donors'

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Recurring donors';
-- END INCREMENTAL

SET @segmentation_id := (SELECT id FROM segmentation WHERE name = 'Recurring donors');
SET @not_recurring := (SELECT id FROM segment WHERE name = 'Not a recurring donor');
SET @failed := (SELECT id FROM segment WHERE name = 'Failed recurring donor');
SET @past := (SELECT id FROM segment WHERE name = 'Past recurring donor');
SET @curr := (SELECT id FROM segment WHERE name = 'Current recurring donor');

CREATE TEMPORARY TABLE event_history (
  contact_id INT UNSIGNED NOT NULL,
  event_date DATETIME NOT NULL,
  donation_id INT UNSIGNED,
  donation_status INT UNSIGNED NOT NULL,
  action_id INT UNSIGNED
);

-- All contacts are not a recurring donor when they are created
INSERT INTO event_history (contact_id, event_date, donation_status)
  SELECT
    c.id, c.created_at, @not_recurring
  FROM contact c
;

-- All contacts become recurring donors when a (unpaid for now) recurring donation is created
INSERT INTO event_history
  SELECT
    a.contact_id, d.started_at, d.id, @curr, a.id
  FROM donation d
  JOIN action a ON a.id = d.action_id
  WHERE d.frequency_unit != 'one-off'
;

-- A donation with no successful payment becomes current at first successful payment
INSERT INTO event_history (contact_id, event_date, donation_id, donation_status)
  SELECT
    a.contact_id, MIN(p.receive_date), d.id, @curr
  FROM donation d
  JOIN action a ON a.id = d.action_id
  JOIN payment f ON f.donation_id = d.id AND f.status != 'success'
  JOIN payment p ON p.donation_id = d.id AND p.receive_date > f.receive_date
  LEFT JOIN payment s ON s.donation_id = d.id AND s.status = 'success' AND s.receive_date < f.receive_date
  WHERE d.frequency_unit != 'one-off' AND p.status = 'success' AND s.id IS NULL
  GROUP BY a.contact_id, d.id
;

-- A donor becomes past when a donation with at least one payment is ended and there are no current donation
INSERT INTO event_history (contact_id, event_date, donation_id, donation_status)
  SELECT
    DISTINCT a.contact_id, d.ended_at, d.id, @past
  FROM donation d
  JOIN action a ON a.id = d.action_id
  JOIN payment p ON p.donation_id = d.id
  LEFT JOIN action a_curr ON a_curr.contact_id = a.contact_id
  LEFT JOIN donation d_curr ON d_curr.action_id = a_curr.id AND d_curr.frequency_unit != 'one-off' AND (d_curr.ended_at IS NULL OR d_curr.ended_at > d.ended_at)
  LEFT JOIN payment p_curr ON p_curr.donation_id = d_curr.id AND p_curr.receive_date < d.ended_at
  WHERE d.frequency_unit != 'one-off' AND d.ended_at IS NOT NULL
  GROUP BY a.contact_id, d.id
  HAVING SUM(p_curr.status = 'success') = 0 OR SUM(p_curr.status = 'success') IS NULL
;

-- A donor becomes failed when an unpaid donation is ended and there are no current or past donation
INSERT INTO event_history (contact_id, event_date, donation_id, donation_status)
  SELECT
    a.contact_id, d.ended_at, d.id, @failed
  FROM donation d
  JOIN action a ON a.id = d.action_id
  LEFT JOIN payment p ON p.donation_id = d.id
  LEFT JOIN action a_curr ON a_curr.contact_id = a.contact_id
  LEFT JOIN donation d_curr ON d_curr.action_id = a_curr.id AND d_curr.frequency_unit != 'one-off' AND d_curr.id != d.id
  LEFT JOIN payment p_curr ON p_curr.donation_id = d_curr.id AND p_curr.receive_date < d.ended_at
  WHERE d.frequency_unit != 'one-off' AND d.ended_at IS NOT NULL AND p.id IS NULL
  GROUP BY a.contact_id, d.id
  HAVING SUM(p_curr.status = 'success') = 0 OR SUM(p_curr.status = 'success') IS NULL
;

-- A donor becomes failed when the first payment of a donation is failed and there are no current or past donation
INSERT INTO event_history (contact_id, event_date, donation_id, donation_status)
  SELECT
    a.contact_id, MIN(f.receive_date), d.id, @failed
  FROM donation d
  JOIN action a ON a.id = d.action_id
  JOIN payment f ON f.donation_id = d.id AND f.status != 'success'
  LEFT JOIN payment p ON p.donation_id = d.id AND p.receive_date < f.receive_date AND p.status = 'success'
  LEFT JOIN action a_curr ON a_curr.contact_id = a.contact_id
  LEFT JOIN donation d_curr ON d_curr.action_id = a_curr.id AND d_curr.frequency_unit != 'one-off' AND d_curr.id != d.id
  LEFT JOIN payment p_curr ON p_curr.donation_id = d_curr.id AND p_curr.receive_date < f.receive_date
  WHERE d.frequency_unit != 'one-off' AND p.id IS NULL
  GROUP BY a.contact_id, d.id
  HAVING SUM(p_curr.status = 'success') = 0 OR SUM(p_curr.status = 'success') IS NULL
;

DROP TABLE IF exists segment_history;
CREATE TABLE segment_history (
  contact_id INT UNSIGNED NOT NULL,
  event_date DATETIME,
  trigger_action_id INT UNSIGNED,
  leaved INT,
  joined INT NOT NULL,
  prev_contact INT UNSIGNED NOT NULL,
  INDEX (contact_id, event_date),
  CONSTRAINT `fk_segment_history_leaved`
    FOREIGN KEY (`leaved`)
    REFERENCES `segment` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_segment_history_joined`
    FOREIGN KEY (`joined`)
    REFERENCES `segment` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION

);

SELECT @prev_contact := NULL;
INSERT INTO segment_history
  SELECT
    contact_id,
    event_date,
    action_id,
    IF (@prev_contact != contact_id, NULL, @joined),
    @joined := donation_status,
    @prev_contact := contact_id
  FROM event_history
  ORDER BY contact_id, event_date
;

-- This query skips records where joined_at=left_at
INSERT INTO contact_segment
  (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id)

  SELECT 
    s.segmentation_id, s.id, j.contact_id, j.event_date, MIN(l.event_date), j.trigger_action_id
  FROM segment s
  JOIN segment_history j ON j.joined = s.id AND (j.leaved IS NULL OR j.leaved != j.joined)
  LEFT JOIN segment_history l ON l.leaved = s.id AND l.contact_id = j.contact_id AND l.leaved != l.joined AND l.event_date >= j.event_date
  WHERE s.segmentation_id = @segmentation_id AND (l.event_date IS NULL OR l.event_date != j.event_date)
  GROUP BY s.id, j.contact_id, j.event_date, j.trigger_action_id
;

DROP TABLE event_history;
DROP TABLE segment_history;
