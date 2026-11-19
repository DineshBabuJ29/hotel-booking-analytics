-- =====================================================================
-- 03  DATA QUALITY CHECKS
-- Portable SQL (MySQL 8 and SQLite). Each query is named "-- @name: x";
-- python/s02_build_database.py saves every result to outputs/sql_results/.
-- =====================================================================

-- @name: row_counts_by_hotel_year
SELECT hotel, arrival_date_year, COUNT(*) AS bookings
FROM fact_bookings
GROUP BY hotel, arrival_date_year
ORDER BY hotel, arrival_date_year;

-- @name: duplicate_profile
-- Exact duplicates are kept (no booking ID exists to prove they are errors).
-- Which segments are they in? Mostly groups, which supports keeping them.
SELECT market_segment,
       COUNT(*)                                                        AS bookings,
       SUM(is_exact_duplicate)                                         AS exact_duplicates,
       ROUND(100.0 * SUM(is_exact_duplicate) / COUNT(*), 1)            AS duplicate_pct
FROM fact_bookings
GROUP BY market_segment
ORDER BY exact_duplicates DESC;

-- @name: deposit_type_anomaly
-- 'Non Refund' bookings cancel almost always: a known anomaly in this dataset.
SELECT deposit_type, market_segment,
       COUNT(*)                                       AS bookings,
       ROUND(100.0 * AVG(is_canceled), 1)             AS cancel_rate_pct
FROM fact_bookings
GROUP BY deposit_type, market_segment
HAVING COUNT(*) >= 100
ORDER BY deposit_type, bookings DESC;

-- @name: value_ranges
SELECT MIN(adr) AS min_adr, MAX(adr) AS max_adr, ROUND(AVG(adr), 2) AS avg_adr,
       MIN(lead_time) AS min_lead, MAX(lead_time) AS max_lead,
       SUM(is_day_use) AS day_use_bookings,
       SUM(CASE WHEN adr = 0 THEN 1 ELSE 0 END) AS zero_price_bookings
FROM fact_bookings;
