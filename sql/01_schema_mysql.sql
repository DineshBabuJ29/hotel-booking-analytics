-- =====================================================================
-- 01  MySQL 8 SCHEMA  (run first, then 02_load_mysql.sql)
-- Mirrors data/processed/ written by python/s01_clean_transform.py
-- =====================================================================
CREATE DATABASE IF NOT EXISTS hotel_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hotel_analytics;

DROP TABLE IF EXISTS fact_bookings;
DROP TABLE IF EXISTS dim_country;

CREATE TABLE dim_country (
  country       VARCHAR(5)  PRIMARY KEY,
  bookings      INT         NOT NULL,
  country_name  VARCHAR(60) NOT NULL,
  is_domestic   TINYINT     NOT NULL
);

CREATE TABLE fact_bookings (
  booking_id                      INT           PRIMARY KEY,
  hotel                           VARCHAR(20)   NOT NULL,
  is_canceled                     TINYINT       NOT NULL,
  lead_time                       INT           NOT NULL,
  arrival_date_year               SMALLINT      NOT NULL,
  arrival_date_month              VARCHAR(10)   NOT NULL,
  arrival_date_week_number        TINYINT       NOT NULL,
  arrival_date_day_of_month       TINYINT       NOT NULL,
  stays_in_weekend_nights         INT           NOT NULL,
  stays_in_week_nights            INT           NOT NULL,
  adults                          INT           NOT NULL,
  children                        INT           NOT NULL,
  babies                          INT           NOT NULL,
  meal                            VARCHAR(5)    NOT NULL,
  country                         VARCHAR(5)    NOT NULL,
  market_segment                  VARCHAR(20)   NOT NULL,
  distribution_channel            VARCHAR(20)   NOT NULL,
  is_repeated_guest               TINYINT       NOT NULL,
  previous_cancellations          INT           NOT NULL,
  previous_bookings_not_canceled  INT           NOT NULL,
  reserved_room_type              CHAR(1)       NOT NULL,
  assigned_room_type              CHAR(1)       NOT NULL,
  booking_changes                 INT           NOT NULL,
  deposit_type                    VARCHAR(12)   NOT NULL,
  agent                           INT           NOT NULL,
  company                         INT           NOT NULL,
  days_in_waiting_list            INT           NOT NULL,
  customer_type                   VARCHAR(20)   NOT NULL,
  adr                             DECIMAL(8,2)  NOT NULL,
  required_car_parking_spaces     INT           NOT NULL,
  total_of_special_requests       INT           NOT NULL,
  reservation_status              VARCHAR(10)   NOT NULL,
  reservation_status_date         DATE          NOT NULL,
  is_exact_duplicate              TINYINT       NOT NULL,
  arrival_date                    DATE          NOT NULL,
  booking_date                    DATE          NOT NULL,
  arrival_month                   CHAR(7)       NOT NULL,
  arrival_month_num               TINYINT       NOT NULL,
  arrival_month_name              CHAR(3)       NOT NULL,
  arrival_week_start              DATE          NOT NULL,
  arrival_weekday                 CHAR(3)       NOT NULL,
  season                          VARCHAR(6)    NOT NULL,
  room_nights                     INT           NOT NULL,
  is_day_use                      TINYINT       NOT NULL,
  guests                          INT           NOT NULL,
  is_family                       TINYINT       NOT NULL,
  booking_value                   DECIMAL(10,2) NOT NULL,
  realized_revenue                DECIMAL(10,2) NOT NULL,
  lost_revenue                    DECIMAL(10,2) NOT NULL,
  is_paid_stay                    TINYINT       NOT NULL,
  is_online_ta                    TINYINT       NOT NULL,
  channel_group                   VARCHAR(40)   NOT NULL,
  lead_time_bucket                VARCHAR(20)   NOT NULL,
  is_room_upgrade_or_change       TINYINT       NOT NULL,
  has_special_requests            TINYINT       NOT NULL,
  is_no_show                      TINYINT       NOT NULL,
  KEY ix_hotel_month (hotel, arrival_month),
  KEY ix_country (country),
  CONSTRAINT fk_country FOREIGN KEY (country) REFERENCES dim_country (country)
);
