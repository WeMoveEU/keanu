-- IGNORE
create table euro (currency varchar(3), day DATETIME, price decimal(8,4));
-- prepare the data
-- rename 's/ /_/g' *.csv
-- sed -ib 's/ [%]//g' *.csv
-- sed -ib 's/"//g' *.csv
-- 

-- sed -ib '1 s/^.*$/day,price,open,high,low,change/' *.csv


-- Data from both Yahoo Finance and Google Finance have been unreliable for over
-- a year. Suggest that you investigate other financial data aggregators; some
-- very good free ones are Tiingo, Barchart, and Quandl. Each has a very easy
-- API (application programming interface) and they only require you to register
-- an email address. There are restrictions on the amount of data you can grab
-- everyday, but those limits are very generous for a single investor.

