-- ORDER: 44
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = s.segmentation_id WHERE sn.name = 'Active status'

-- TAGS: strategy=group_reduce

SET @membership := (SELECT id FROM segmentation WHERE name = 'Membership');
SET @membership_member := (SELECT id FROM segment
                             WHERE segmentation_id = @membership AND name = 'Member');
SET @membership_expiring := (SELECT id FROM segment
                              WHERE segmentation_id = @membership AND name = 'Expiring');
SET @membership_expired := (SELECT id FROM segment
                              WHERE segmentation_id = @membership AND name = 'Expired');

SET @active_status := (SELECT id FROM segmentation WHERE name = 'Active status');
SET @active_notmember := (SELECT id FROM segment WHERE name = 'Not a member');
SET @active_inactive := (SELECT id FROM segment WHERE name = 'Inactive');
SET @active_active := (SELECT id FROM segment WHERE name = 'Active');

SET @hot_contact_now := NOW();
-- BEGIN INCREMENTAL
SET @recent := last_sync_dt('hot_contact', 'civicrm');

-- Create list of contacts who did something recently or who may have become inactive recently
DROP TABLE IF EXISTS hot_contact;
CREATE TABLE hot_contact (
  id INT NOT NULL PRIMARY KEY
);

INSERT IGNORE INTO hot_contact 
  SELECT id FROM ${SOURCE}.civicrm_contact WHERE modified_date >= @recent
;

INSERT IGNORE INTO hot_contact
  SELECT contact_id FROM contact_segment WHERE segmentation_id = @membership AND joined_at >= @recent
;

-- This could maybe be optimised by looking only at the latest activity of each contact
INSERT IGNORE INTO hot_contact
  SELECT contact_id FROM action WHERE created_at >= @recent
                                   OR DATE_ADD(created_at, INTERVAL 3 MONTH) BETWEEN @recent AND @hot_contact_now;
;

DELETE cs FROM contact_segment cs JOIN hot_contact h ON h.id = cs.contact_id WHERE segmentation_id = @active_status;
-- END INCREMENTAL


-- grouping = contact_id INT
-- new_grouping BOOL
-- sequence = engage_at DATETIME -- member join or action
-- accumulators:
--     acc_start_at DATETIME -- last pair start
--     acc_opt_end_at DATETIME -- last pair end
--     acc_trigger_action_id INT -- last target_action_id
--     acc_last_closed BOOLEAN --  retro look it if carryover are closed
-- current:
--    notmember_at DATETIME -- when is the end of membership for this engagement
-- emit:
--    joined_at = acc_start_at 
--    max(left_at) = acc_opt_end_at
--    => group by 1

-- ACCUMULATOR FUNCATIONS ---
DROP FUNCTION IF EXISTS acc_start_at;
DROP FUNCTION IF EXISTS acc_opt_end_at;
DROP FUNCTION IF EXISTS acc_last_closed;

DELIMITER //
CREATE FUNCTION acc_start_at (new_grouping BOOLEAN,
                              engaged_at DATETIME,
                              closed BOOLEAN,
                              start_at DATETIME)
RETURNS DATETIME
BEGIN

IF new_grouping OR closed THEN
   RETURN engaged_at;
ELSE
   RETURN start_at;
END IF;

END
//
DELIMITER ;

DELIMITER //
CREATE FUNCTION acc_opt_end_at (engaged_at DATETIME,
                                notmember_at DATETIME)
RETURNS DATETIME
BEGIN
DECLARE expiry DATETIME;
SET expiry := DATE_ADD(engaged_at, INTERVAL 3 MONTH);

IF notmember_at < expiry THEN
   RETURN notmember_at;
ELSE
   RETURN expiry;
END IF;

END
//
DELIMITER ;

-- retro accumulator --- 
DELIMITER //
CREATE FUNCTION acc_last_closed (engaged_at DATETIME,
                            opt_end_at DATETIME,
                            new_grouping BOOLEAN)
RETURNS BOOLEAN
BEGIN

IF new_grouping OR opt_end_at < engaged_at THEN
  RETURN TRUE;
ELSE
  RETURN FALSE;
END IF;

END
//
DELIMITER ;


-- INITIALIZE
SET @grouping := NULL, @new_grouping := NULL;
SET @acc_last_closed := FALSE, @acc_start_at := NULL, @acc_opt_end_at := NULL, @acc_trigger_action_id := NULL;

INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id)
  SELECT @active_status, @active_active, contact_id, joined_at, left_at, trigger_action_id
    FROM (
      SELECT
        -- helper var 
        @new_grouping := IF (@grouping = contact_id, FALSE, TRUE),
        -- retro accumulators / emit or close flag
        @acc_last_closed := acc_last_closed(engaged_at, @acc_opt_end_at, @new_grouping) as insert_it,
        -- emiters
        @grouping AS contact_id,
        @acc_start_at as joined_at,
        @acc_opt_end_at as left_at,
        @acc_trigger_action_id AS trigger_action_id,
        -- carry over accumulators
        @acc_start_at := acc_start_at(@new_grouping, engaged_at, @acc_last_closed, @acc_start_at),
        @acc_opt_end_at := acc_opt_end_at(engaged_at, notmember_at),
        @acc_trigger_action_id := trigger_action_id,

        -- update grouping vars
        @grouping := contact_id

      FROM ( -- ordered_engagement_moments = actions done when Contact was a member
        SELECT
          a.contact_id,
          a.created_at as engaged_at,
          cs.left_at as notmember_at,
          a.id as trigger_action_id
        FROM action a
        JOIN action_page ap ON ap.id = a.action_page_id
        JOIN contact c ON c.id = a.contact_id
        JOIN contact_segment cs ON cs.contact_id = a.contact_id
                                AND cs.segment_id = @membership_member
                                AND cs.joined_at <= a.created_at
                                AND (cs.left_at > a.created_at OR cs.left_at IS NULL)
        -- BEGIN INCREMENTAL
        JOIN hot_contact h ON a.contact_id = h.id
        -- END INCREMENTAL
        WHERE ap.action_type != 'consent' AND a.created_at >= DATE_ADD(c.created_at, INTERVAL 24 HOUR)
        ORDER BY contact_id, engaged_at
      ) ordered_engagement_moments
    ) cs
  WHERE contact_id IS NOT NULL AND insert_it
;

-- FINALIZE
INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id)
VALUES (@active_status, @active_active,
       @grouping,
       @acc_start_at, @acc_opt_end_at,
       @acc_trigger_action_id);


UPDATE contact_segment cs SET left_at = NULL
  WHERE cs.segment_id = @active_active AND cs.left_at > NOW();
;


-- CLEANUP
DROP FUNCTION IF EXISTS acc_start_at;
DROP FUNCTION IF EXISTS acc_opt_end_at;
DROP FUNCTION IF EXISTS acc_last_closed;


-- -----------------------------------------------------------------
-- - Not a member segment -- just copy from the Membership - glueing expiring and expired (if exists)
-- -----------------------------------------------------------------
INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id)
SELECT
 @active_status, 
 @active_notmember, 
 expiring.contact_id, 
 expiring.joined_at, 
 IF(expired.id IS NOT NULL, expired.left_at, expiring.left_at), 
 expiring.trigger_action_id
FROM contact_segment expiring
LEFT JOIN contact_segment expired
       ON expiring.contact_id = expired.contact_id
       AND expired.segment_id = @membership_expired
       AND expiring.left_at = expired.joined_at 
-- BEGIN INCREMENTAL
JOIN hot_contact h ON expiring.contact_id = h.id
-- END INCREMENTAL
WHERE  expiring.segment_id = @membership_expiring 
;

-- ----------------------------------------------------------------
-- - Inactive -----------------------------------------------------
-- ----------------------------------------------------------------

DROP FUNCTION IF EXISTS emit_start;
DROP FUNCTION IF EXISTS emit_end;


DELIMITER //
CREATE FUNCTION emit_start (new_grouping BOOLEAN, acc_last_left_at DATETIME, joined_at DATETIME)
RETURNS DATETIME
BEGIN
  IF new_grouping OR joined_at IS NULL
  THEN
    RETURN acc_last_left_at;
  ELSE
    IF acc_last_left_at != joined_at -- does this span touch the previous?
      THEN RETURN acc_last_left_at;
      ELSE RETURN NULL;
    END IF;
  END IF;
END
//
DELIMITER ;

DELIMITER //
CREATE FUNCTION emit_end (new_grouping BOOLEAN, joined_at DATETIME)
RETURNS DATETIME
BEGIN
  IF new_grouping
  THEN RETURN NULL;
  ELSE RETURN joined_at;
  END IF;
END
//
DELIMITER ;


SET @grouping := -1, @new_grouping := FALSE;
SET @acc_last_left_at := NULL;

INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at)
  SELECT @active_status, @active_inactive, contact_id, joined_at, left_at
  FROM (
    SELECT
      @new_grouping := IF (@grouping = contact_id, FALSE, TRUE),

      @grouping as contact_id,
      emit_start(@new_grouping, @acc_last_left_at, joined_at) as joined_at,
      emit_end(@new_grouping, joined_at) as left_at,

      @acc_last_left_at := left_at,

      @grouping := contact_id
    FROM (
      SELECT 
        contact_id, joined_at, left_at, segment_id
      FROM (
        SELECT
          cs.contact_id, cs.joined_at, cs.left_at, cs.segment_id
        FROM contact_segment cs
        -- BEGIN INCREMENTAL
        JOIN hot_contact h ON cs.contact_id = h.id
        -- END INCREMENTAL
        WHERE cs.segment_id IN (@active_notmember, @active_active)
      UNION
        SELECT -- Fake record for contact creation
          c.id AS contact_id, created_at AS joined_at, created_at AS left_at, 0 AS segment_id
        FROM contact c
        -- BEGIN INCREMENTAL
        JOIN hot_contact h ON c.id = h.id
        -- END INCREMENTAL
      ) moments
      ORDER BY contact_id, joined_at, IFNULL(left_at, NOW())
    ) ord
  ) res
  WHERE joined_at IS NOT NULL
;

INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at)
  SELECT * FROM (
    SELECT
      @active_status, @active_inactive,
      @grouping as contact_id,
      emit_start(TRUE, @acc_last_left_at, NULL) as joined_at,
      emit_end(TRUE, NULL) as left_at
  ) x
  WHERE joined_at is not null
;

SELECT save_last_sync_dt('hot_contact', 'civicrm', @hot_contact_now);
-- BEGIN INCREMENTAL
DROP TABLE hot_contact;
-- END INCREMENTAL
