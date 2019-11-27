-- ORDER: 6
DROP FUNCTION IF EXISTS date_trunc_day;

CREATE FUNCTION date_trunc_day (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN date(d);


DROP FUNCTION IF EXISTS date_trunc_month;

CREATE FUNCTION date_trunc_month (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(CONCAT(date_format(d, '%Y-%m'), '-01') , '%Y-%m-%d');


DROP FUNCTION IF EXISTS date_trunc_quarter;

CREATE FUNCTION date_trunc_quarter (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(CONCAT(date_format(d, '%Y-'), (quarter(d)-1)*3+1, '-01') , '%Y-%m-%d');


DROP FUNCTION IF EXISTS date_trunc_year;

CREATE FUNCTION date_trunc_year (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(CONCAT(date_format(d, '%Y-'), '01-01') , '%Y-%m-%d');


DROP FUNCTION IF EXISTS query_param;
DELIMITER //
CREATE FUNCTION query_param (url text, param char(32))
RETURNS TEXT DETERMINISTIC
BEGIN
  DECLARE param_pos INT;
  DECLARE param_length INT;
  DECLARE param_end_pos INT;
  SET param_pos = LOCATE(param, url);

  IF param_pos = 0 THEN
    RETURN NULL;
  ELSE
    SET param_end_pos = LOCATE('&', url, param_pos);
    SET param_length = LENGTH(param);
    IF param_end_pos = 0 THEN
      RETURN SUBSTRING(url, param_pos + param_length + 1);
    ELSE
      RETURN SUBSTRING(url, param_pos + param_length + 1, param_end_pos - param_pos - param_length - 1);
    END IF;
  END IF;
END
//
DELIMITER ;
