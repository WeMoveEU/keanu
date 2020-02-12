-- ORDER: 3
-- TRUNCATE last_sync
-- Just overwrite the rows with INSERT IGNORE INTO
-- BEGIN INITIAL
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
-- END INITIAL
