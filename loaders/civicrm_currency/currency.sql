-- TRUNCATE currency
-- ORDER: 1

-- BEGIN INITIAL
INSERT INTO currency (code, rate)
SELECT name, value
FROM ${SOURCE}.civicrm_option_value where option_group_id = (
       SELECT id FROM ${SOURCE}.civicrm_option_group WHERE name = 'euro_rates'
       );
-- END INITIAL
