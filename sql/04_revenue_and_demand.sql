-- =====================================================================
-- 04  REVENUE & DEMAND
--   Q1  Headline KPIs per hotel
--   Q2  Monthly realized revenue, ADR and cancellations, with YoY growth
--   Q3  Seasonality: which months earn the most and charge the most?
--   Q4  Like-for-like growth, Jan-Aug 2017 vs Jan-Aug 2016
-- Concepts: CASE, conditional aggregation, CTEs, LAG, self-join.
-- =====================================================================

-- @name: headline_kpis
-- Q1
SELECT hotel,
       COUNT(*)                                                       AS bookings,
       ROUND(100.0 * AVG(is_canceled), 1)                             AS cancel_rate_pct,
       ROUND(SUM(realized_revenue), 0)                                AS realized_revenue,
       ROUND(SUM(lost_revenue), 0)                                    AS lost_revenue,
       ROUND(100.0 * SUM(lost_revenue) / SUM(booking_value), 1)       AS lost_share_pct,
       ROUND(SUM(CASE WHEN is_canceled = 0 THEN room_nights ELSE 0 END), 0) AS stayed_room_nights,
       ROUND(1.0 * SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN booking_value ELSE 0 END)
             / SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN room_nights ELSE 0 END), 2) AS realized_adr,
       ROUND(AVG(CASE WHEN is_canceled = 0 THEN room_nights END), 2)  AS avg_stay_nights,
       ROUND(AVG(lead_time), 0)                                       AS avg_lead_time_days
FROM fact_bookings
GROUP BY hotel;

-- @name: monthly_trend
-- Q2. Realized ADR = revenue / room-nights of stays that happened.
WITH m AS (
  SELECT hotel, arrival_month,
         COUNT(*)                                       AS bookings,
         AVG(is_canceled)                               AS cancel_rate,
         SUM(realized_revenue)                          AS revenue,
         SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN booking_value ELSE 0 END)
           / SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN room_nights ELSE 0 END) AS adr
  FROM fact_bookings
  GROUP BY hotel, arrival_month
)
SELECT hotel, arrival_month, bookings,
       ROUND(100.0 * cancel_rate, 1)                                        AS cancel_rate_pct,
       ROUND(revenue, 0)                                                    AS realized_revenue,
       ROUND(adr, 2)                                                        AS realized_adr,
       ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (PARTITION BY hotel ORDER BY arrival_month))
             / LAG(revenue, 12) OVER (PARTITION BY hotel ORDER BY arrival_month), 1) AS revenue_yoy_pct
FROM m
ORDER BY hotel, arrival_month;

-- @name: seasonality
-- Q3. Average over all years for each calendar month.
SELECT hotel, arrival_month_num, arrival_month_name,
       COUNT(*)                                                       AS bookings,
       ROUND(100.0 * AVG(is_canceled), 1)                             AS cancel_rate_pct,
       ROUND(SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN booking_value ELSE 0 END)
             / SUM(CASE WHEN is_canceled = 0 AND is_paid_stay = 1 THEN room_nights ELSE 0 END), 2) AS realized_adr,
       RANK() OVER (PARTITION BY hotel ORDER BY SUM(realized_revenue) DESC) AS revenue_rank
FROM fact_bookings
GROUP BY hotel, arrival_month_num, arrival_month_name
ORDER BY hotel, arrival_month_num;

-- @name: yoy_jan_aug
-- Q4. The data covers Jul-2015 to Aug-2017, so Jan-Aug is the only like-for-like window.
WITH y AS (
  SELECT hotel, arrival_date_year AS yr,
         COUNT(*) AS bookings, SUM(realized_revenue) AS revenue, AVG(is_canceled) AS cancel_rate
  FROM fact_bookings
  WHERE arrival_month_num BETWEEN 1 AND 8 AND arrival_date_year IN (2016, 2017)
  GROUP BY hotel, arrival_date_year
)
SELECT cur.hotel, cur.yr AS year_, cur.bookings, ROUND(cur.revenue, 0) AS realized_revenue,
       ROUND(100.0 * cur.cancel_rate, 1)                              AS cancel_rate_pct,
       ROUND(100.0 * (cur.revenue - prev.revenue) / prev.revenue, 1)  AS revenue_yoy_pct
FROM y cur
LEFT JOIN y prev ON prev.hotel = cur.hotel AND prev.yr = cur.yr - 1
ORDER BY cur.hotel, cur.yr;
