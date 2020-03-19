-- ORDER: 40
-- DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id WHERE s.external_id IS NOT NULL AND s.external_system = 'civicrm_group'

-- How this works:
-- Filtering the group subscription history --
-- these queries could be simpler with window functions and CTE's
-- first i'm using a temp table because I cannot use CTE to self-join a query result.
-- also, i have to use some @variable trickery to rank rows (something I could do with window function easily)
-- Using variables requires to nest the queries, so I produce 1. Sorted data -> 2. Ranked data -> 3. Filtered data
-- in this order.

SET @last_contact := (SELECT MAX(id) FROM contact);

DROP TABLE IF EXISTS group_history;

CREATE TABLE group_history -- temporary table to track group join and leave
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
            ${SOURCE}.civicrm_subscription_history
        WHERE
            status in ('Added', 'Removed')
            AND group_id IN (SELECT external_id FROM segment WHERE external_system = 'civicrm_group')
        ORDER BY 1, 2, 3
            ) subq2

        ) subq1
        
-- topmost query just filters the status changes (ignoring series of adds or removals)
WHERE subq1.status_change = 1;



CREATE INDEX group_history_contact_id ON group_history (contact_id);
CREATE INDEX group_history_group_id ON group_history (group_id);
-- * --- * --- * -- 


-- BEGIN INCREMENTAL
DELETE cs FROM contact_segment cs JOIN segment s ON cs.segment_id = s.id
WHERE s.external_id IS NOT NULL AND s.external_system = 'civicrm_group'
;
-- END INCREMENTAL


INSERT INTO contact_segment -- insert contacts' segments based on groups
    (segmentation_id, segment_id, contact_id, joined_at, left_at)
SELECT DISTINCT
    s.segmentation_id,
    s.id,
    ghj.contact_id,
    ghj.date,
    ghl.date
FROM group_history ghj
-- find the ending time of this group membership
    LEFT JOIN group_history ghl
    ON ghj.group_id = ghl.group_id AND ghj.contact_id = ghl.contact_id AND ghj.order_rank + 1 = ghl.order_rank
    JOIN
    segment s ON ghj.group_id = s.external_id AND s.external_system = 'civicrm_group'

WHERE ghj.status = 'Added' AND (ghl.date IS NULL OR DATEDIFF(ghl.date, ghj.date) > 0)
  AND ghj.contact_id <= @last_contact
;

DROP TABLE group_history;

