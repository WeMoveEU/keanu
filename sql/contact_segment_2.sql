-- ORDER: 61
-- TRUNCATE contact_segment
-- Active segments
-- create table activity_history

SET @rank = 0;
SET @prev_contact_id = NULL;

DROP TABLE IF EXISTS action_history;

CREATE TABLE action_history
SELECT
contact_id,
created_at,
action_id,
@rank := IF(@prev_contact_id = contact_id, @rank + 1, 1) as rank,
@prev_contact_id := contact_id
FROM (
 SELECT
  act.contact_id,
  act.created_at,
  act.id as action_id
 FROM action act JOIN contact con ON
   con.id = act.contact_id

 ORDER BY 1,2
) ordered_actions

;

CREATE INDEX contact_id_idx ON action_history (contact_id);
CREATE INDEX created_at_idx ON action_history (created_at);
CREATE INDEX campaign_id ON action_history (action_id);
CREATE INDEX rank_id  ON action_history (rank);


SET @last_created_at = NULL;
SET @prev_contact_id2 = NULL;
SET @days = 91; -- 3 months
SET @min_days = 30; -- month
-- SET @days = 182; -- 6 months
SET @segment_id = (SELECT id from segment where name = 'Active 3 month');
SET @segmentation_id = (SELECT segmentation_id from segment where name = 'Active 3 month');

-- BEGIN INCREMENTAL
DELETE FROM contact_segment where segmentation_id = @segmentation_id;
-- END INCREMENTAL

INSERT into contact_segment (contact_id, segmentation_id, segment_id, joined_at, left_at)
SELECT
  contact_id,
  @segmentation_id,
  @segment_id,
  joined_at,
  max(left_at) as left_at

FROM (
SELECT
ah.contact_id,
-- initialize for next contact
@last_created_at := IF (ah.contact_id = @prev_contact_id2, @last_created_at, NULL),
@joined_at := IF (
                 datediff(ah.created_at, @last_created_at) <= @days
                 AND
                 datediff(ah.created_at, @joined_at) >= @min_days,
                 @joined_at,
                 ah.created_at) as joined_at,
ah.created_at + interval @days day as left_at,

@last_created_at := ah.created_at,
@prev_contact_id2 := ah.contact_id

FROM action_history ah
where rank > 1
) x

GROUP BY 1,2,3,4
HAVING count(*) > 1 -- remove 
;
