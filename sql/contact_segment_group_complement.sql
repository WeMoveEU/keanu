-- ORDER: 61
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = cs.segmentation_id WHERE sn.name = 'Membership' AND s.name IN ('Expiring', 'Expired')

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = cs.segmentation_id WHERE sn.name = 'Membership' AND s.name IN ('Expiring', 'Expired');

-- END INCREMENTAL

-- Get the ids of segments for easier use and initialize variables
SET @sn = (SELECT id FROM segmentation sn WHERE sn.name = 'Membership');

SET @seg_member = (SELECT s.id FROM segment s JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name = 'Membership' AND s.name = 'Member');

SET @seg_expired = (SELECT s.id FROM segment s JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name = 'Membership' AND s.name = 'Expired');

SET @seg_expiring = (SELECT s.id FROM segment s JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name = 'Membership' AND s.name = 'Expiring');

SET @cc = NULL; -- track current contact
SET @rank = 0;

-- Create a table where for each member we have their joins and leaves,
-- as well as actions done when they were not members (where join_at = left_at)
-- numbered (ranked by order)
-- This is so we can later iterate over pairs of such membership eccurances.
DROP TABLE IF EXISTS membership_ranked;

CREATE TABLE membership_ranked
SELECT
    contact_id,
    joined_at,
    left_at,
    is_member,
    trigger_action_id,
    @rank := CASE WHEN contact_id = @cc THEN @rank + 1 ELSE 0 END as rank,
    @cc := contact_id
FROM
    (
    SELECT
      contact_id, joined_at, left_at, is_member, trigger_action_id
    FROM
      (
      -- Member segment
      SELECT
        cs.contact_id, cs.joined_at, cs.left_at, TRUE as is_member, NULL as trigger_action_id
      FROM contact_segment cs
           JOIN segment s ON cs.segment_id = s.id
      WHERE s.id = @seg_member

      UNION
      -- ACTIONS make expiring longer
      SELECT
        a.contact_id, a.created_at, a.created_at, FALSE as is_member, a.id as trigger_action_id
      FROM action a
           LEFT JOIN contact_segment cs ON
           cs.segment_id = @seg_member AND 
           a.contact_id = cs.contact_id AND
           cs.joined_at <= a.created_at AND (a.created_at < cs.left_at OR cs.left_at IS NULL)
      WHERE cs.id IS NULL
      UNION
      SELECT
        c.id, c.created_at, c.created_at, FALSE as is_member, NULL as trigger_action_id
      FROM contact c
-- BEGIN INCREMENTAL
      JOIN activated ON c.contact_id = activated.contact_id
-- END INCREMENTAL

      ) x

    ORDER BY contact_id, joined_at
    ) ordered;

CREATE INDEX membership_ranked_idx ON membership_ranked (contact_id, rank);

-- When doing bulk inserts into tables with auto-increment columns, set innodb_autoinc_lock_mode to 2 instead of the default value 1. See Section 14.6.1.6, “AUTO_INCREMENT Handling in InnoDB” for details. -- from https://dev.mysql.com/doc/refman/5.7/en/optimizing-innodb-bulk-data-loading.html

-- Now insert into expiring contacts:
-- We insert it after someone left the segment

SET @cc = NULL; -- track current contact
SET @last_left_at = NULL; -- used to track if we are in a continuation (if == 0)


INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at, trigger_action_id) -- INSERT Expiring
SELECT
@sn, @seg_expiring,
contact_id, expiring_start as joined_at, left_at,
trigger_action_id
FROM (
SELECT
  m1.contact_id,
  @expiring_start := CAST(CASE WHEN m1.contact_id = @cc AND m1.is_member IS FALSE AND @last_left_at = 0
                          -- just did action, continue expiring
                               THEN @expiring_start
                          -- was member for a while
                          WHEN m1.contact_id = @cc AND m1.is_member IS TRUE
                               THEN m1.left_at
                          -- Initial value (both was member and did action)
                          ELSE m1.left_at END AS DATETIME) as expiring_start,
  @timeout := DATE_ADD(@expiring_start, interval 1 year),
  @last_left_at := CASE WHEN m2.contact_id IS NULL THEN @timeout -- this is the last event XXX should we mark contacts end in this event in the future?
       WHEN @timeout >= m2.joined_at AND m2.is_member THEN m2.joined_at -- contact joins members again
       WHEN @timeout >= m2.joined_at AND NOT m2.is_member THEN 0 -- 0 is a special value meaning that expiring continues->remove this record
       ELSE @timeout -- this expiring intervall fully fills in the hole
  END as left_at,
  m1.trigger_action_id,
  @cc := m1.contact_id

FROM membership_ranked m1 LEFT JOIN
     membership_ranked m2 ON m1.contact_id = m2.contact_id AND m1.rank + 1 = m2.rank
WHERE m1.left_at IS NOT NULL -- exclude last active member record
) expiry
WHERE
NOT left_at = 0  -- remove continuations (0 is speacial value and means that contact continues to be in this segment)
                 -- sorry for that - NULL is taken for semantic: contact is still in segment NOW.
;

-- XXX We could add here another pass to UPDATE expiring contact_segments with left_at in the future to NULL


DROP TABLE membership_ranked;

UPDATE contact_segment cs SET left_at = NULL
WHERE
cs.segment_id = @seg_expiring AND cs.left_at > NOW();
;

-- Now create expired contact_segment in all the empty spaces between member and expiring cs
-- We create another ranked table because MySQL 5.7 does not have CTEs. Please admins upgrade to version 8.x!

CREATE TABLE membership_ranked
SELECT
    contact_id,
    joined_at,
    left_at,
    @rank := CASE WHEN contact_id = @cc THEN @rank + 1 ELSE 0 END as rank,
    @cc := contact_id
FROM
    (
    SELECT
      contact_id, joined_at, left_at
    FROM
      contact_segment cs
    WHERE cs.segment_id IN (@seg_member, @seg_expiring)

    ORDER BY contact_id, joined_at
    ) ordered;

CREATE INDEX membership_ranked_idx ON membership_ranked (contact_id, rank);


INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at) -- INSERT Expired
SELECT
@sn, @seg_expired,
m1.contact_id,
m1.left_at as joined_at,
m2.joined_at as left_at

FROM membership_ranked m1 LEFT JOIN
membership_ranked m2 ON m1.contact_id = m2.contact_id AND m1.rank + 1 = m2.rank
WHERE
  (m1.left_at IS NOT NULL AND m2.joined_at is NULL) -- only finished spans
  OR
  (m1.left_at IS NOT NULL AND m2.joined_at IS NOT NULL AND m1.left_at != m2.joined_at) -- or spans that do not touch
;



DROP TABLE membership_ranked;
