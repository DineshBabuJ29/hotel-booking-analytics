-- =====================================================================
-- 02  LOAD CSVs INTO MySQL 8
-- 1. Run python/run_all.py first.
-- 2. Enable local loading: SET GLOBAL local_infile = 1;  and, in Workbench:
--    Edit connection -> Advanced -> Others: OPT_LOCAL_INFILE=1
-- 3. Change the folder path if your project is elsewhere (use forward slashes).
-- The processed CSVs have no empty cells, so no NULL handling is needed.
-- =====================================================================
USE hotel_analytics;

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Hotel_Booking_Analytics/data/processed/dim_country.csv'
INTO TABLE dim_country
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Hotel_Booking_Analytics/data/processed/fact_bookings.csv'
INTO TABLE fact_bookings
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

SELECT 'fact_bookings' AS t, COUNT(*) AS n FROM fact_bookings
UNION ALL SELECT 'dim_country', COUNT(*) FROM dim_country;
SHOW WARNINGS LIMIT 20;
