-- ORDER: 59
-- At this point we have loaded basic data: contacts, actions, donations, broadcast events
-- We can create a helper table hot_contact to mark contacts that did something since we last checked
-- The time we last checked will be saved only 


-- BEGIN INCREMENTAL
DROP TABLE IF EXISTS hot_contact;

CREATE TABLE hot_contact (
       id INT not null,
       new_actions BOOLEAN NOT NULL,
       new_consents BOOLEAN NOT NULL,
       group_change BOOLEAN NOT NULL
);

SET @recent := last_sync_dt('hot_contact', 'civicrm');
SET @hot_contact_now := NOW();

INSERT INTO hot_contact
SELECT
c.id,
count(a.id) > 0 as new_actions,
count(cons.id) > 0 as new_consents,
count(grp_io.id) >0 as group_change

FROM
contact c

LEFT JOIN action a ON c.id = a.contact_id AND a.created_at > @recent
LEFT JOIN action_page ap ON ap.id = a.action_page_id AND ap.action_type <> 'consent'

LEFT JOIN action cons ON c.id = cons.contact_id AND c.created_at > @recent
LEFT JOIN action_page cons_ap ON cons_ap.id = cons.action_page_id AND cons_ap.action_type = 'consent'

LEFT JOIN ${SOURCE}.civicrm_subscription_history grp_io
     ON grp_io.contact_id = c.id
     AND status in ('Added', 'Removed')
     AND date > @recent
     AND grp_io.group_id IN
                          (SELECT external_id FROM segment WHERE external_system = 'civicrm_group')


group by c.id
HAVING
count(a.id) > 0 OR
count(cons.id) > 0 OR
count(grp_io.id) > 0
;

CREATE INDEX hot_contact_id on hot_contact (id);

SELECT save_last_sync_dt('hot_contact', 'civicrm', @hot_contact_now);
-- END INCREMENTAL
