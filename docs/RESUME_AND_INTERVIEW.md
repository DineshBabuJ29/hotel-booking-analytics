# Resume Entry & Interview Preparation

> Numbers below come from `outputs/INSIGHTS_REPORT.md` (real-data run). If you change the analysis, rerun and update them.

## Resume entry
**Hotel Booking Demand: Channel, Cancellation & Revenue Analytics (119k bookings)** | [GitHub link]
*SQL · Python (scikit-learn) · Excel · Power BI (DAX)*

- Analysed 119k bookings across 6 sales channels with **SQL (window functions, CTEs)** and Python. Found that online travel agencies bring 53% of revenue but keep only **57%** of booked value after cancellations, vs **81%** for direct bookings.
- Built a **cancellation-risk model** (gradient boosting, **ROC-AUC 0.85** on 6 unseen months, leakage-free features). The riskiest 10% of bookings cancel 70% of the time. Designed a targeted deposit policy worth about **€261k net** per 6 months.
- Built an **Excel what-if model** (binomial overbooking optimiser, deposit policy, channel-mix scenarios) and a **4-page Power BI dashboard** (32 DAX measures). Benchmarked weekly demand forecasts and showed a seasonal-naive baseline (9.2% MAPE) beats a regression model.

**Two-bullet version:** keep bullets 1 and 2, and add "Power BI and Excel what-if model" to bullet 2.

### Why this project fits a Digital Commerce Data Analyst role
- **Digital commerce platforms:** online travel agencies *are* commerce platforms. You analysed channel economics, online-share growth and the value of moving customers to the direct (own-website) channel.
- **Revenue growth:** every finding ends in a revenue number (deposits, overbooking, channel mix).
- **SQL and Python:** both are used throughout, plus ML that serves a business decision.

### Honesty rules
- Call it a **personal project on a public, peer-reviewed dataset** (two Portuguese hotels).
- Policy numbers are **estimates under stated assumptions**, not results achieved for a client.
- Know your limitations: duplicates, the Non-Refund anomaly, calibration drift, the channel-shift upper bound.

---

## 60-second pitch (STAR)
**Situation:** two hotels lose 39% of booked value to cancellations, and most bookings now come through online agencies.
**Task:** find which channels and bookings cause the loss, and what to do about it.
**Action:** I cleaned 119k bookings, analysed channels in SQL, and built a cancellation model tested on months it never
saw. I also built an Excel model for deposits and overbooking, and a Power BI dashboard.
**Result:** OTAs keep only 57% of booked value vs 81% for direct bookings. The model's riskiest 10% cancel 70% of the
time. A deposit only on those bookings would protect about €261k net per half-year, and overbooking 2 rooms per 100
adds revenue with almost no walked guests.

## Interview questions to practise
**Data and judgment**
1. *You kept 32k duplicate rows. Why?* No booking ID, and groups legitimately repeat. They are flagged, and the sensitivity check shows the channel conclusions hold.
2. *What is data leakage? Give an example from your project.* Parking requests show 0% cancellation, so the field is probably filled at check-in, and using it would be cheating.
3. *Why a time-based split instead of a random one?* A random split lets the model see the future, so its score would be too optimistic.

**Machine learning**
4. *ROC-AUC vs accuracy? Why not accuracy?* AUC measures ranking. With a 40% base rate, accuracy hides the trade-offs.
5. *Your probabilities were too low in the test months. What does that mean?* Calibration drift: cancellations rose. Ranking still works; recalibrate (Platt/isotonic) on recent data.
6. *Why did gradient boosting barely beat logistic regression?* Most of the signal is in a few strong categorical drivers; a simple model gets most of it. That is also why the simple model is a sensible baseline.
7. *What is permutation importance?* Shuffle one feature and measure how much AUC drops.

**Forecasting**
8. *Why did the simple forecast win?* Two years of data is too little to fit trend + seasonality reliably. Always beat a naive baseline before using a complex model.
9. *MAPE vs MAE?* MAPE is relative, so it's easy to explain; MAE is in units and isn't distorted by small actual values.

**Excel / business**
10. *Explain your overbooking model.* Show-ups follow a binomial distribution. Expected revenue = ADR x expected occupied rooms - walk cost x expected walked guests. Choose the X that maximises it.
11. *Why only late cancellations for overbooking?* Rooms cancelled weeks ahead get resold. Only last-minute losses need covering.
12. *How would you test the deposit policy for real?* A/B test: randomly apply the deposit to half of the high-risk bookings, and compare net revenue and conversion.

**SQL (live)**
13. Revenue YoY by hotel and month (`LAG(x, 12) OVER (PARTITION BY hotel ...)`). 14. Channel share of total (`SUM() OVER ()`).
15. Stack several trait breakdowns into one table (`UNION ALL`). 16. Cancellation rate by lead-time bucket (`CASE`).
