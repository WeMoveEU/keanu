-- PREFERENCE: 50
-- civicrm_group_contact
-- based on groups (which)

-- filtering the subscription history
-- these queries could be simpler with window functions and CTE's
-- first i'm using a temp table because I cannot use CTE to self-join a query result.
-- also, i have to use some @variable trickery to rank rows (something I could do with window function easily)
-- Using variables requires to nest the queries, so I produce 1. Sorted data -> 2. Ranked data -> 3. Filtered data
-- in this order.

create table group_history 
SELECT group_id, contact_id, date, status, order_rank 

FROM (
 -- Subquery that counts status changes per (group,contact) - assumes sorted data
 SELECT
 group_id,
 contact_id,
 date,
 status,
 @order_rank := IF(@prev_contact = contact_id,
                  IF ( @prev_status != status, -- is status change?
                       @order_rank + 1,           -- yes, increase order_rank counter!
                       @order_rank),              -- no, keep the counter same
                1)                                                                            AS order_rank,
                -- initialize the @prev_status to Removed on new contact seen
 @prev_status := IF (@prev_contact = contact_id, @prev_status, 'Removed'),  
                -- and check the status, if changed (for current contact)
 IF ( @prev_status <> status, TRUE, FALSE)                                                 AS status_change,
 @prev_contact := contact_id,
 @prev_status := status 

 FROM (
  -- Subquery that generates SORTED data
  SELECT group_id, contact_id, date, status
  FROM
    wemove_47.civicrm_subscription_history
  WHERE
    status in ('Added', 'Removed')
  AND group_id IN (SELECT external_id FROM segment)
  ORDER BY 1, 2, 3
 ) subq2

) subq1
-- topmost query just filters the status changes (ignoring series of adds or removals)
WHERE subq1.status_change = 1 ;



CREATE INDEX group_history_contact_id ON group_history (contact_id);
CREATE INDEX group_history_group_id ON group_history (group_id);
-- * --- * --- * -- 


INSERT INTO contact_segment
(segmentation_id, segment_id,
contact_id, joined_at, left_at 
)
SELECT DISTINCT
 s.segmentation_id,
 s.id,
 ghj.contact_id,
 ghj.date,
 ghl.date
FROM group_history ghj
 -- only take contacts we still process
 JOIN contact c ON ghj.contact_id = c.id
 -- find the ending time of this group membership
 LEFT JOIN group_history ghl
 ON ghj.group_id = ghl.group_id AND ghj.contact_id = ghl.contact_id AND ghj.order_rank + 1 = ghl.order_rank
JOIN
 segment s ON ghj.group_id = s.external_id

WHERE ghj.status = 'Added'

;

DROP TABLE group_history;


----- -=================
-- problematic contact_id = 25446
-- ERROR 1062 (23000): Duplicate entry '5-1-21-2015-09-04 10:43:49' for key 'one_segment_in_segmentation_at_a_time'
-- 21

SELECT DISTINCT
s.segmentation_id,
s.id,
ghj.contact_id,
ghj.date,
ghl.date
FROM group_history ghj
-- only take contacts we still process
JOIN contact c ON ghj.contact_id = c.id
-- find the ending time of this group membership
LEFT JOIN group_history ghl
ON ghj.group_id = ghl.group_id AND ghj.contact_id = ghl.contact_id AND ghj.order_rank + 1 = ghl.order_rank
JOIN
segment s ON ghj.group_id = s.external_id

WHERE ghj.status = 'Added'
and c.id = 21
