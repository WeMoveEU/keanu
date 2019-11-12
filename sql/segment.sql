-- ORDER: 11
-- DELETE FROM segment
    --
-- MEMBERSHIP
SET @membership = (select id from segmentation where name = 'Membership');

INSERT INTO segment (name, segmentation_id, external_id) values ('Member', @membership, 42);

-- LANGUAGE
SET @language = (select id from segmentation where name = 'Language');

INSERT INTO segment (name, segmentation_id, external_id)
SELECT
    title,
    @language,
    id
FROM
    wemove_47.civicrm_group
WHERE
    parents = 32;

SET @country_interest = (select id from segmentation where name = 'Country interest');

INSERT INTO segment (name, segmentation_id, external_id)
SELECT
    title,
    @country_interest,
    id
FROM
    wemove_47.civicrm_group
WHERE
    parents = 10;

-- COUNTRIES

SET @country = (select id from segmentation where name = 'Country');

-- Active

INSERT INTO segment (name, segmentation_id, external_id)
SELECT
    s.name,
    s.id,
    NULL
FROM segmentation s
WHERE s.name like 'Active%';
