-- ORDER: 2
drop table if exists calendar;

create table calendar (
       dt date not null primary key,
       y smallint null,
       q tinyint null,
       m tinyint null,
       d tinyint null,
       dw tinyint null,
       monthname varchar(9) null,
       dayname varchar(9) null,
       w tinyint null,
       isWeekday binary(1) null
       );


-- can't self-join a temporary table in mysql. duh!
create table tmp_ints ( i tinyint );
insert into tmp_ints values (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);

insert into calendar (dt) select date('2010-01-01') + interval a.i*10000 + b.i*1000 + c.i*100 + d.i*10 + e.i day
from tmp_ints a join tmp_ints b join tmp_ints c join tmp_ints d join tmp_ints e
where (a.i*10000 + b.i*1000 + c.i*100 + d.i*10 + e.i) <= 11322 order by 1;
drop table tmp_ints;

update calendar set
       isWeekday = case
                 when dayofweek(dt) in (1,7) then 0
                 else 1
                 end,
       y = year(dt),
       q = quarter(dt),
       m = month(dt),
       d = dayofmonth(dt),
       dw = dayofweek(dt),
       monthname = monthname(dt),
       dayname = dayname(dt),
       w = week(dt);
   
-- TODO: indexes


create index calendar_y ON calendar (y);
create index calendar_q ON calendar (q);
create index calendar_m ON calendar (m);
create index calendar_d ON calendar (d);
