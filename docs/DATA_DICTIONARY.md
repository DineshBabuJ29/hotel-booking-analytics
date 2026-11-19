# Data Dictionary

## Source
**Hotel booking demand datasets.** Nuno Antonio, Ana de Almeida, Luis Nunes, *Data in Brief* 22 (2019) 41-49.
These are real booking records from two hotels in Portugal (H1 = Resort Hotel in the Algarve, H2 = City Hotel in Lisbon),
for arrivals between 1 July 2015 and 31 August 2017. Guest and hotel identities were removed by the authors.
The copy used here is `hotels.csv` from the TidyTuesday project (2020-02-11).
The paper does not state the currency; it is assumed to be EUR (the hotels are in Portugal).

## Business definitions (identical in SQL, Python, Excel and DAX)
| Term | Definition |
|---|---|
| Booking | One row of the file (there is no booking ID; `booking_id` is a surrogate key added in cleaning) |
| Cancelled | `is_canceled = 1`: includes no-shows (`reservation_status = 'No-Show'`) |
| Room nights | weekend nights + week nights |
| ADR | Average Daily Rate: price per room-night |
| Booking value | ADR x room nights |
| Realized revenue | Booking value of bookings that were **not** cancelled |
| Lost revenue | Booking value of cancelled bookings |
| Revenue kept % | Realized revenue / booking value |
| Realized ADR | Realized revenue / room nights, over paid stays (ADR > 0 and nights > 0) |
| OTA | Online travel agency (`market_segment = 'Online TA'`, e.g. Booking.com, Expedia) |
| Lead time | Days between booking and arrival |
| Late cancellation | Cancelled within 3 days of arrival, or no-show (used for overbooking) |

## fact_bookings (one row per booking)
Original columns (see the paper) plus these derived fields:

| Column | Meaning |
|---|---|
| booking_id | Surrogate key |
| is_exact_duplicate | 1 = identical to an earlier row (kept; see the report) |
| arrival_date, booking_date | Real dates (booking date = arrival - lead time) |
| arrival_month, arrival_month_num/name, arrival_week_start, arrival_weekday, season | Calendar fields |
| room_nights, is_day_use, guests, is_family | Stay and party |
| booking_value, realized_revenue, lost_revenue, is_paid_stay | Money |
| is_online_ta, channel_group | Channel (Online travel agency, Offline agency / tour operator, Direct, Groups, Corporate, Other) |
| lead_time_bucket | 0-7, 8-30, 31-90, 91-180, 181-365, 365+ days |
| is_room_upgrade_or_change | Assigned room type differs from reserved (known only at check-in; not used in the model) |
| has_special_requests, is_no_show | Flags |

## Model and forecast tables
| Table | Content |
|---|---|
| model_metrics | ROC-AUC, PR-AUC, Brier, accuracy, and AUC on No-Deposit bookings, per model |
| model_deciles | Test-period No-Deposit bookings grouped by predicted risk (1 = riskiest 10%) |
| model_importance | Permutation importance: drop in ROC-AUC when each feature is shuffled |
| model_scores | Risk score per test booking |
| forecast_weekly | Weekly stays, plus 3 forecasts for the 16 held-out weeks |

## Leakage rules (features the model must NOT use)
| Column | Why it is excluded |
|---|---|
| reservation_status, reservation_status_date | They are the outcome itself |
| assigned_room_type, booking_changes | Happen after the booking |
| required_car_parking_spaces | 0% of bookings with a parking request cancel, so it is almost certainly recorded at check-in |
