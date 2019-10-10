DROP FUNCTION date_trunc_day;

CREATE FUNCTION date_trunc_day (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(date_format(d, '%Y-%m-%d'), '%Y-%m-%d');


DROP FUNCTION date_trunc_month;

CREATE FUNCTION date_trunc_month (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(CONCAT(date_format(d, '%Y-%m'), '-01') , '%Y-%m-%d');


DROP FUNCTION date_trunc_quarter;

CREATE FUNCTION date_trunc_quarter (d DATETIME)
RETURNS DATETIME DETERMINISTIC
RETURN str_to_date(CONCAT(date_format(d, '%Y-'), (quarter(d)-1)*3+1, '-01') , '%Y-%m-%d');
