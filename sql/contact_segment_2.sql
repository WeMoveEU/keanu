-- Active segments
-- create table activity_history

SET @rank = 0;
SET @prev_contact_id = NULL;


CREATE TABLE action_history
SELECT
contact_id,
created_at,
activity_type_id,
campaign_id,
@rank := IF(@prev_contact_id = contact_id, @rank + 1, 1) as rank,
@prev_contact_id := contact_id
FROM (
 SELECT
  actcon.contact_id,
  act.activity_date_time as created_at,
  act.activity_type_id,
  act.campaign_id
 FROM wemove_47.civicrm_activity act JOIN wemove_47.civicrm_activity_contact actcon ON
   actcon.activity_id = act.id

 WHERE act.activity_type_id IN (32, 54, 59, 28)
 ORDER BY 1,2
) ordered_actions

;

CREATE INDEX contact_id_idx ON action_history (contact_id);
CREATE INDEX created_at_idx ON action_history (created_at);
CREATE INDEX campaign_id ON action_history (campaign_id);
CREATE INDEX rank_id  ON action_history (rank);


SET @last_created_at = NULL;
SET @prev_contact_id2 = NULL;
SET @days = 91; -- 3 months
-- SET @days = 182; -- 6 months
SET @segment_id = (SELECT id from segment where name = 'Active 3 month');
SET @segmentation_id = (SELECT segmentation_id from segment where name = 'Active 3 month');

INSERT into contact_segment (contact_id, segmentation_id, segment_id, joined_at, left_at)
SELECT
  contact_id, @segmentation_id, @segment_id, joined_at, max(left_at) as left_at

FROM (
SELECT
ah.contact_id,
-- initialize for next contact
@last_created_at := IF (ah.contact_id = @prev_contact_id2, @last_created_at, NULL),
@joined_at := IF (datediff(ah.created_at, @last_created_at) <= @days, @joined_at, ah.created_at) as joined_at,
ah.created_at + interval @days day as left_at,

@last_created_at := ah.created_at,
@prev_contact_id2 := ah.contact_id

FROM action_history ah JOIN contact c ON ah.contact_id = c.id
where rank > 1
) x

GROUP BY 1,2,3,4
;
