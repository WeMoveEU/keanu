
DROP TABLE IF EXISTS `keanu`.`currency`;

CREATE TABLE IF NOT EXISTS `keanu`.`currency` (
  code varchar(3) not null,
  rate decimal(10,4) not null
);

CREATE INDEX currency_code_unique ON currency (code);
