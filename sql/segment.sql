-- ORDER: 11
-- DELETE FROM segment
--
-- MEMBERSHIP
-- BEGIN INITIAL
set @membership = (select id from segmentation where name = 'Membership');

insert into segment (name, segmentation_id, external_id) values ('Member', @membership, 42);

-- LANGUAGE
set @language = (select id from segmentation where name = 'Language');

insert into segment (name, segmentation_id, external_id)
SELECT
  title,
  @language,
  id
FROM
${SOURCE}.civicrm_group
WHERE
parents = 32;

set @country_interest = (select id from segmentation where name = 'Country interest');

insert into segment (name, segmentation_id, external_id)
SELECT
title,
@country_interest,
id
FROM
${SOURCE}.civicrm_group
WHERE
parents = 10;

-- COUNTRIES

set @country = (select id from segmentation where name = 'Country');

-- Active

INSERT INTO segment (name, segmentation_id, external_id)
SELECT
s.name,
s.id,
NULL
FROM segmentation s
WHERE s.name like 'Active%';

-- END INITIAL
