-- =====================================================================
-- 06  CANCELLATIONS & GUEST BEHAVIOUR
--   Q9   How much revenue do cancellations cost, by hotel and channel?
--   Q10  Which booking traits go with cancellations? (deposit, repeat guest,
--        special requests, previous cancellations, parking)
--   Q11  Families vs couples vs groups: stay length, spend, cancellations
--   Q12  Do repeat guests behave differently?
-- =====================================================================

-- @name: lost_revenue_by_hotel_channel
-- Q9
SELECT hotel, channel_group,
       COUNT(*)                                                         AS bookings,
       SUM(is_canceled)                                                 AS cancellations,
       ROUND(100.0 * AVG(is_canceled), 1)                               AS cancel_rate_pct,
       ROUND(SUM(lost_revenue), 0)                                      AS lost_revenue,
       ROUND(100.0 * SUM(lost_revenue) / SUM(SUM(lost_revenue)) OVER (PARTITION BY hotel), 1) AS share_of_hotel_lost_pct
FROM fact_bookings
GROUP BY hotel, channel_group
ORDER BY hotel, lost_revenue DESC;

-- @name: cancellation_drivers
-- Q10. One row per trait value. UNION ALL stacks several GROUP BYs into one table.
SELECT 'Special requests' AS trait,
       CASE WHEN total_of_special_requests = 0 THEN '0' WHEN total_of_special_requests = 1 THEN '1' ELSE '2+' END AS value_,
       COUNT(*) AS bookings, ROUND(100.0 * AVG(is_canceled), 1) AS cancel_rate_pct
FROM fact_bookings
GROUP BY CASE WHEN total_of_special_requests = 0 THEN '0' WHEN total_of_special_requests = 1 THEN '1' ELSE '2+' END
UNION ALL
SELECT 'Previous cancellations',
       CASE WHEN previous_cancellations = 0 THEN '0' ELSE '1+' END,
       COUNT(*), ROUND(100.0 * AVG(is_canceled), 1)
FROM fact_bookings
GROUP BY CASE WHEN previous_cancellations = 0 THEN '0' ELSE '1+' END
UNION ALL
SELECT 'Repeat guest', CASE WHEN is_repeated_guest = 1 THEN 'Yes' ELSE 'No' END,
       COUNT(*), ROUND(100.0 * AVG(is_canceled), 1)
FROM fact_bookings
GROUP BY CASE WHEN is_repeated_guest = 1 THEN 'Yes' ELSE 'No' END
UNION ALL
SELECT 'Parking requested', CASE WHEN required_car_parking_spaces > 0 THEN 'Yes' ELSE 'No' END,
       COUNT(*), ROUND(100.0 * AVG(is_canceled), 1)
FROM fact_bookings
GROUP BY CASE WHEN required_car_parking_spaces > 0 THEN 'Yes' ELSE 'No' END
UNION ALL
SELECT 'Booked through agent', CASE WHEN agent > 0 THEN 'Yes' ELSE 'No' END,
       COUNT(*), ROUND(100.0 * AVG(is_canceled), 1)
FROM fact_bookings
GROUP BY CASE WHEN agent > 0 THEN 'Yes' ELSE 'No' END;

-- @name: guest_type_profile
-- Q11
SELECT CASE WHEN is_family = 1 THEN 'Family (children/babies)'
            WHEN adults = 1 THEN 'Solo'
            WHEN adults = 2 THEN 'Couple / pair'
            ELSE 'Group of adults' END                                AS guest_type,
       COUNT(*)                                                       AS bookings,
       ROUND(100.0 * AVG(is_canceled), 1)                             AS cancel_rate_pct,
       ROUND(AVG(CASE WHEN is_canceled = 0 THEN room_nights END), 2)  AS avg_stay_nights,
       ROUND(AVG(CASE WHEN is_paid_stay = 1 THEN adr END), 2)         AS avg_adr,
       ROUND(AVG(CASE WHEN is_canceled = 0 THEN booking_value END), 0) AS avg_stay_value
FROM fact_bookings
GROUP BY CASE WHEN is_family = 1 THEN 'Family (children/babies)'
              WHEN adults = 1 THEN 'Solo'
              WHEN adults = 2 THEN 'Couple / pair'
              ELSE 'Group of adults' END
ORDER BY bookings DESC;

-- @name: repeat_guests
-- Q12
SELECT hotel,
       ROUND(100.0 * AVG(is_repeated_guest), 1)                                          AS repeat_guest_pct,
       ROUND(100.0 * AVG(CASE WHEN is_repeated_guest = 1 THEN is_canceled END), 1)       AS repeat_cancel_pct,
       ROUND(100.0 * AVG(CASE WHEN is_repeated_guest = 0 THEN is_canceled END), 1)       AS new_cancel_pct,
       ROUND(AVG(CASE WHEN is_repeated_guest = 1 AND is_paid_stay = 1 THEN adr END), 2)  AS repeat_adr,
       ROUND(AVG(CASE WHEN is_repeated_guest = 0 AND is_paid_stay = 1 THEN adr END), 2)  AS new_adr
FROM fact_bookings
GROUP BY hotel;
