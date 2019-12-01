-- ORDER: 52
-- DELETE FROM recipient

-- Store which broadcasts are going to be added to recipients table to then update recipient counts
CREATE TEMPORARY TABLE updated_broadcast AS
  SELECT b.id
  FROM broadcast b LEFT JOIN recipient r ON r.broadcast_id = b.id
  WHERE r.id IS NULL
;

INSERT INTO recipient (contact_id, broadcast_id, external_system, external_id)
  SELECT
    contact_id, b.id, 'civicrm_mailing_recipients', MIN(mr.id)
  FROM ${SOURCE}.civicrm_mailing_recipients mr
  JOIN broadcast b ON b.external_id=mr.mailing_id AND b.external_system='civicrm_mailing'
-- BEGIN INCREMENTAL
  WHERE (contact_id, b.id) NOT IN (SELECT contact_id, broadcast_id FROM recipient)
-- END INCREMENTAL
-- recipients table can have several entries for same contact and mailing
  GROUP BY contact_id, b.id
;

UPDATE broadcast b JOIN (
    SELECT bt.id AS id, COUNT(*) AS recipients
    FROM updated_broadcast bt
    JOIN recipient r ON bt.id = r.broadcast_id
    GROUP BY bt.id
  ) t ON b.id=t.id
  SET b.recipient_count = t.recipients
;

DROP TABLE updated_broadcast;
