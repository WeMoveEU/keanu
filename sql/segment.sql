-- PREFERENCE: 11
--
-- MEMBERSHIP
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
wemove_47.civicrm_group
WHERE
parents = 32;

set @country_interest = (select id from segmentation where name = 'Country interest');

insert into segment (name, segmentation_id, external_id)
SELECT
title,
@country_interest,
id
FROM
wemove_47.civicrm_group
WHERE
parents = 10;

-- COUNTRIES

set @country = (select id from segmentation where name = 'Country');


