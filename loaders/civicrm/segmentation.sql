-- ORDER: 10
-- DELETE FROM segmentation
-- Members: 42
-- Country interest: 10 (perent)
-- Languages: 32
-- XXX - what is 'UK members' (64)

-- BEGIN INITIAL
INSERT INTO segmentation (name, external_id, external_system)
VALUES
('Everyone', NULL, NULL),
('Membership', 42, 'civicrm_group'),
('Mailing list', 32, 'civicrm_group'),
('Preferred language', 77, 'civicrm_option_group'),
('Active status', 122, 'civicrm_option_group'),
('Recurring donors', 121, 'civicrm_option_group'),
('Country', NULL, NULL)
;

-- END INITIAL
