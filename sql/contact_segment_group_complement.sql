-- ORDER: 61
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = cs.segmentation_id WHERE sn.name = 'Membership' AND s.name IN ('Expiring', 'Expired')

-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id JOIN segmentation sn ON sn.id = cs.segmentation_id WHERE sn.name = 'Membership' AND s.name IN ('Expiring', 'Expired');

-- END INCREMENTAL

-- Get the ids of segments for easier use and initialize variables
SET @sn = (SELECT id FROM segmentation sn WHERE sn.name = 'Membership');

SET @seg_expired = (SELECT s.id FROM segment s JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name ='Membership' AND s.name = 'Expired');

SET @seg_expiring = (SELECT s.id FROM segment s JOIN segmentation sn ON s.segmentation_id = sn.id
    WHERE sn.name ='Membership' AND s.name = 'Expiring');

SET @cc = NULL; -- track current contact
SET @rank = 0;

-- Create a table where for each member we have their joins and leaves, numbered (ranked by order)
-- This is so we can later iterate over pairs of such membership eccurances.
DROP TABLE IF EXISTS membership_ranked;

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
        cs.contact_id, cs.joined_at, cs.left_at
    FROM contact_segment cs
        JOIN segment s ON cs.segment_id = s.id
        JOIN segmentation sn ON cs.segmentation_id = sn.id
    WHERE s.name = 'Member' and sn.name = 'Membership'
    ORDER BY contact_id, joined_at
        ) ordered;

CREATE INDEX membership_ranked_idx ON membership_ranked (contact_id, rank);

-- When doing bulk inserts into tables with auto-increment columns, set innodb_autoinc_lock_mode to 2 instead of the default value 1. See Section 14.6.1.6, “AUTO_INCREMENT Handling in InnoDB” for details. -- from https://dev.mysql.com/doc/refman/5.7/en/optimizing-innodb-bulk-data-loading.html

-- Now insert into expiring contacts:
-- We insert it after someone left the segment

INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at) -- INSERT Expiring
SELECT
  @sn, @seg_expiring, m1.contact_id,
  m1.left_at as joined_at,
  -- calculate one year from leaving members:
  CASE
    WHEN DATE_ADD(m1.left_at, interval 1 year) > m2.joined_at THEN m2.joined_at
    WHEN DATE_ADD(m1.left_at, interval 1 year) > NOW() THEN NULL
    ELSE DATE_ADD(m1.left_at, interval 1 year)
  END as left_at
FROM
  membership_ranked m1 LEFT JOIN
  membership_ranked m2 ON m1.contact_id = m2.contact_id AND m1.rank + 1 = m2.rank
WHERE
  m1.left_at IS NOT NULL -- left members
;

INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at) -- INSERT Expiring
SELECT
  @sn, @seg_expiring, c.id,
  c.created_at as joined_at,
  CASE
  WHEN DATE_ADD(c.created_at, interval 1 year) > NOW() THEN NULL
  ELSE DATE_ADD(c.created_at, interval 1 year)
  END as left_at
FROM
  contact c LEFT JOIN
  membership_ranked m ON c.id = m.contact_id
WHERE m.contact_id IS NULL -- not found
;


INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at) -- INSERT Expired
SELECT
@sn, @seg_expired, m1.contact_id,
-- calculate one year from leaving members:
DATE_ADD(m1.left_at, interval 1 year) as joined_at,
m2.joined_at as left_at
FROM
membership_ranked m1 LEFT JOIN
membership_ranked m2 ON m1.contact_id = m2.contact_id AND m1.rank + 1 = m2.rank
WHERE
m1.left_at IS NOT NULL -- left members
AND
DATE_ADD(m1.left_at, interval 1 year) < COALESCE(m2.joined_at, NOW()) -- it fits
;



INSERT INTO contact_segment (segmentation_id, segment_id, contact_id, joined_at, left_at) -- INSERT Expired
SELECT
@sn, @seg_expired, c.id,
DATE_ADD(c.created_at, interval 1 year) as joined_at,
NULL as left_at
FROM
contact c LEFT JOIN
membership_ranked m ON c.id = m.contact_id
WHERE m.contact_id IS NULL -- not found
AND DATE_ADD(c.created_at, interval 1 year) <= NOW()
;



DROP TABLE membership_ranked;
