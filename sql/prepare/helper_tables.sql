-- to remove data:
-- TRUNCATE calendar
-- ORDER: 80
drop table if exists calendar;

create table calendar (
        dt date not null primary key,
        y smallint not null,
        m tinyint not null,
        d tinyint not null,
        q tinyint not null,
        w tinyint not null,
        dw tinyint not null,
        day_name varchar(9) not null,
        month_name varchar(9) not null,
        isWeekday boolean not null,
        UNIQUE td_ymd_idx (y, m, d)
        );

DROP PROCEDURE IF EXISTS fill_calendar;
    DELIMITER //
CREATE PROCEDURE fill_calendar(IN startdate DATE, IN stopdate DATE)
    BEGIN
    DECLARE currentdate DATE;
SET currentdate = startdate;
    WHILE currentdate < stopdate DO
INSERT INTO calendar VALUES (
        currentdate,
        YEAR(currentdate),
        MONTH(currentdate),
        DAY(currentdate),
        QUARTER(currentdate),
        WEEKOFYEAR(currentdate),
        DAYOFWEEK(currentdate),
        DATE_FORMAT(currentdate,'%W'),
        DATE_FORMAT(currentdate,'%M'),
        DAYOFWEEK(currentdate) NOT IN (1,7)
        );
SET currentdate = ADDDATE(currentdate,INTERVAL 1 DAY);
    END WHILE;
    END
    //
    DELIMITER ;


TRUNCATE TABLE calendar;

CALL fill_calendar('2015-01-01','2021-01-01');
