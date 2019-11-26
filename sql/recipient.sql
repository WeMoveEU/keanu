-- ORDER: 52
-- DELETE FROM recipient

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
