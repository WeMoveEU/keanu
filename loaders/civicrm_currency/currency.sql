-- TRUNCATE currency
-- ORDER: 1

drop table if exists currency;

create table currency (
       code varchar(3) not null,
       rate decimal(10,4) not null
);

CREATE INDEX currency_code_unique ON currency (code);


INSERT INTO currency (code, rate)
SELECT name, value
FROM ${SOURCE}.civicrm_option_value where option_group_id = (
       SELECT id FROM ${SOURCE}.civicrm_option_group WHERE name = 'euro_rates'
       );
