-- ORDER: 11
-- DELETE FROM segment

SET @query_start := NOW();

-- BEGIN INITIAL
-- Special Everyone segment
SET @everyone = (SELECT id FROM segmentation WHERE name = 'Everyone');
INSERT INTO segment (name, segmentation_id) VALUES ('Everyone', @everyone);

-- MEMBERSHIP
-- Membership
set @seg = (select id from segmentation where name = 'Membership');
set @ext_id = (select external_id from segmentation where name = 'Membership');

insert into segment (name, segmentation_id, external_id, external_system)
            values ('Member', @seg, @ext_id, 'civicrm_group'),
                   ('Expiring', @seg, NULL, NULL),
                   ('Expired', @seg, NULL, NULL);

-- Mailing list
set @seg = (select id from segmentation where name = 'Mailing list');
set @ext_id = (select external_id from segmentation where name = 'Mailing list');

insert into segment (name, segmentation_id, external_id, external_system)
SELECT
  title,
  @seg,
  id, 'civicrm_group'
FROM
${SOURCE}.civicrm_group
WHERE
parents = @ext_id;

-- Preferred language
set @seg = (select id from segmentation where name = 'Preferred language');
set @ext_id = (select external_id from segmentation where name = 'Preferred language');

insert into segment (name, segmentation_id, external_id, external_system)
SELECT
ov.name,
@seg,
ov.id,
'civicrm_option_value'
FROM
${SOURCE}.civicrm_option_group og
JOIN ${SOURCE}.civicrm_option_value ov ON ov.option_group_id = og.id COLLATE utf8_general_ci
JOIN (SELECT DISTINCT preferred_language FROM contact) pf ON ov.name = pf.preferred_language COLLATE utf8_general_ci
WHERE og.id = @ext_id;


-- COUNTRIES

set @seg = (select id from segmentation where name = 'Country');

INSERT INTO segment (name, segmentation_id, external_id, external_system)
  SELECT
    substring_index(c.name, ',', 1) as name, -- strip "X, republic of", etc.
    @seg,
    c.id, 'civicrm_country'
  FROM (SELECT DISTINCT country FROM contact WHERE country is not null) ctr
  JOIN ${SOURCE}.civicrm_country c ON ctr.country = substring_index(c.name, ',', 1) COLLATE utf8_general_ci
;

-- Active
set @seg = (select id from segmentation where name = 'Active status');
set @ext_id = (select external_id from segmentation where name = 'Active status');

insert into segment (name, segmentation_id, external_id, external_system)
SELECT
ov.label,
@seg,
ov.id,
'civicrm_option_value'
FROM
${SOURCE}.civicrm_option_group og
JOIN ${SOURCE}.civicrm_option_value ov ON ov.option_group_id = og.id
WHERE og.id = @ext_id;

-- Recurring donors
set @seg = (select id from segmentation where name = 'Recurring donors');
set @ext_id = (select external_id from segmentation where name = 'Recurring donors');

insert into segment (name, segmentation_id, external_id, external_system)
SELECT
ov.label,
@seg,
ov.id,
'civicrm_option_value'
FROM
${SOURCE}.civicrm_option_group og
JOIN ${SOURCE}.civicrm_option_value ov ON ov.option_group_id = og.id
WHERE og.id = @ext_id;


-- END INITIAL

SELECT save_last_sync_dt('segment', 'query_start', @query_start);
