-- =====================================================================
-- 05  DISTRIBUTION CHANNELS & PRICING  (the "digital commerce" angle)
--   Q5  Online travel agencies vs direct vs groups: volume, price, cancellations,
--       and revenue that actually materialises
--   Q6  Online share of bookings over time
--   Q7  How does price change with lead time (book early vs late)?
--   Q8  Top source countries: value and reliability
-- Concepts: window shares, running share, NTILE-free bucketing, joins.
-- =====================================================================

-- @name: channel_economics
-- Q5. "Revenue kept %" = realized revenue / value of all bookings made in that channel.
SELECT channel_group,
       COUNT(*)                                                           AS bookings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                 AS booking_share_pct,
       ROUND(AVG(CASE WHEN is_paid_stay = 1 THEN adr END), 2)             AS avg_adr,
       ROUND(100.0 * AVG(is_canceled), 1)                                 AS cancel_rate_pct,
       ROUND(SUM(realized_revenue), 0)                                    AS realized_revenue,
       ROUND(100.0 * SUM(realized_revenue) / SUM(SUM(realized_revenue)) OVER (), 1) AS revenue_share_pct,
       ROUND(100.0 * SUM(realized_revenue) / SUM(booking_value), 1)       AS revenue_kept_pct,
       ROUND(AVG(lead_time), 0)                                           AS avg_lead_time
FROM fact_bookings
GROUP BY channel_group
ORDER BY realized_revenue DESC;

-- @name: online_share_by_quarter
-- Q6
SELECT arrival_date_year AS year_,
       CASE WHEN arrival_month_num <= 3 THEN 'Q1' WHEN arrival_month_num <= 6 THEN 'Q2'
            WHEN arrival_month_num <= 9 THEN 'Q3' ELSE 'Q4' END              AS quarter_,
       COUNT(*)                                                           AS bookings,
       ROUND(100.0 * AVG(is_online_ta), 1)                                AS online_share_pct,
       ROUND(100.0 * SUM(CASE WHEN is_online_ta = 1 THEN realized_revenue ELSE 0 END)
             / SUM(realized_revenue), 1)                                  AS online_revenue_share_pct
FROM fact_bookings
GROUP BY arrival_date_year,
         CASE WHEN arrival_month_num <= 3 THEN 'Q1' WHEN arrival_month_num <= 6 THEN 'Q2'
              WHEN arrival_month_num <= 9 THEN 'Q3' ELSE 'Q4' END
ORDER BY year_, quarter_;

-- @name: lead_time_price_cancel
-- Q7
SELECT lead_time_bucket,
       COUNT(*)                                                   AS bookings,
       ROUND(AVG(CASE WHEN is_paid_stay = 1 THEN adr END), 2)     AS avg_adr,
       ROUND(100.0 * AVG(is_canceled), 1)                         AS cancel_rate_pct,
       ROUND(SUM(lost_revenue), 0)                                AS lost_revenue
FROM fact_bookings
GROUP BY lead_time_bucket
ORDER BY lead_time_bucket;

-- @name: top_countries
-- Q8. Top 15 source countries by realized revenue.
WITH c AS (
  SELECT b.country, d.country_name,
         COUNT(*)                      AS bookings,
         SUM(b.realized_revenue)       AS revenue,
         AVG(b.is_canceled)            AS cancel_rate,
         AVG(CASE WHEN b.is_paid_stay = 1 THEN b.adr END) AS adr
  FROM fact_bookings b
  JOIN dim_country d ON d.country = b.country
  GROUP BY b.country, d.country_name
)
SELECT country, country_name, bookings,
       ROUND(revenue, 0)                                          AS realized_revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1)           AS revenue_share_pct,
       ROUND(100.0 * cancel_rate, 1)                              AS cancel_rate_pct,
       ROUND(adr, 2)                                              AS avg_adr,
       RANK() OVER (ORDER BY revenue DESC)                        AS revenue_rank
FROM c
ORDER BY revenue DESC
LIMIT 15;
