
-- LAST SYNC ID
DROP TABLE IF EXISTS last_sync;

CREATE TABLE last_sync (
       dst VARCHAR(64) not null,
       src VARCHAR(64) not null,
       last_id BIGINT not null
);

CREATE UNIQUE INDEX last_sync_tables_unique ON last_sync (dst, src);


DROP FUNCTION IF EXISTS last_sync_id;

DELIMITER //
CREATE FUNCTION last_sync_id (destination varchar(32), source varchar(32))
RETURNS BIGINT
BEGIN
  DECLARE lid INT;
  SET lid = (SELECT last_id from last_sync WHERE dst=destination AND src=source);

  IF lid IS NULL THEN
     RETURN -1;
  ELSE
     RETURN lid;
  END IF;
END
//
DELIMITER ;

DROP FUNCTION IF EXISTS save_last_sync_id;

DELIMITER //
CREATE FUNCTION save_last_sync_id (destination varchar(32), source varchar(32), last_id2 BIGINT)
RETURNS BIGINT
BEGIN
INSERT INTO last_sync (dst, src, last_id)
SELECT destination, source, last_id2
ON DUPLICATE KEY UPDATE last_id = last_id2;

RETURN last_id2;

END
//
DELIMITER ;

-- LAST SYNC DATE TIME
DROP TABLE IF EXISTS last_sync_dt;

CREATE TABLE last_sync_dt (
dst VARCHAR(64) not null,
src VARCHAR(64) not null,
last_dt DATETIME not null
);

CREATE UNIQUE INDEX last_sync_tables_unique ON last_sync_dt (dst, src);


DROP FUNCTION IF EXISTS last_sync_dt;

DELIMITER //
CREATE FUNCTION last_sync_dt (destination varchar(32), source varchar(32))
RETURNS DATETIME
BEGIN
DECLARE ldt DATETIME;
SET ldt = (SELECT last_dt from last_sync_dt WHERE dst=destination AND src=source);

IF ldt IS NULL THEN
RETURN CAST(0 AS DATETIME);
ELSE
RETURN ldt;
END IF;
END
//
DELIMITER ;

DROP FUNCTION IF EXISTS save_last_sync_dt;

DELIMITER //
CREATE FUNCTION save_last_sync_dt (destination varchar(32), source varchar(32), last_dt2 DATETIME)
RETURNS DATETIME
BEGIN
INSERT INTO last_sync_dt (dst, src, last_dt)
SELECT destination, source, last_dt2
ON DUPLICATE KEY UPDATE last_dt = last_dt2;

RETURN last_dt2;

END
//
DELIMITER ;

