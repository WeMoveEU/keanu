-- Identifies people with more than one primary email
SELECT 
  c.id, c.display_name
  FROM civicrm_contact c
  JOIN civicrm_email e ON c.id=e.contact_id AND e.is_primary
  GROUP BY c.id
  HAVING COUNT(e.id) > 1
;

-- Identifies people with more than one primary address
SELECT 
  c.id, c.display_name
  FROM civicrm_contact c
  JOIN civicrm_address a ON c.id=a.contact_id AND a.is_primary
  GROUP BY c.id
  HAVING COUNT(a.id) > 1
;
