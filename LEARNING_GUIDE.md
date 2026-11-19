# Learning Guide (about 2-3 weeks, 2-3 hours/day)

This project builds on what you learned in the Olist project and adds **machine learning for a business decision,
forecasting, Excel modelling and judgment calls**. Rule: read, run, change something, and predict the result first.

## Week 1: Data, SQL, judgment
| Day | File | What to understand | Exercise |
|---|---|---|---|
| 1 | `data/raw/hotels.csv`, `docs/DATA_DICTIONARY.md` | Every column; which are known at booking time | Mark each column "known at booking" or "known later" |
| 2 | `python/s01_clean_transform.py` | Why each row is removed, why duplicates are kept | Rerun without duplicates: what changes in the report? |
| 3 | `sql/04_revenue_and_demand.sql` | Realized ADR, `LAG(x, 12) PARTITION BY` | Write revenue YoY by **season** yourself |
| 4 | `sql/05_channels_and_pricing.sql` | Revenue kept %, share of total | Add "average booking value" per channel |
| 5 | `sql/06_cancellations_and_guests.sql` | `UNION ALL` of several breakdowns | Add a "meal plan" trait |
| 6 | `python/s03_eda.py` | Sensitivity check (with/without duplicates) | Explain in 2 lines why the channel conclusion is robust |
| 7 | Review | Explain the business problem and findings 1-3 aloud | |

## Week 2: Model, forecast, Excel
| Day | File | What to understand | Exercise |
|---|---|---|---|
| 8 | `python/s04_cancellation_model.py` | Pipeline, ColumnTransformer, one-hot encoding | Remove `deposit_type`: how much does AUC drop? |
| 9 | same | Time split vs random split; ROC-AUC, PR-AUC, Brier | Try a random split. Is the AUC higher? Why is it misleading? |
| 10 | same | Deciles, calibration, permutation importance | Explain the decile chart to a non-technical manager |
| 11 | `python/s05_demand_forecast.py` | Seasonal naive, Fourier terms, MAE vs MAPE | Change the holdout to 8 weeks. Does the winner change? |
| 12 | `excel/Hotel_Revenue_WhatIf.xlsx` | BINOM.DIST grid, SUMPRODUCT, INDEX/MATCH | Set walk cost to 4x ADR. What is the best overbooking level now? |
| 13 | Excel, Deposit and Channel sheets | Which numbers are data and which are assumptions | Find the walk-away rate where the deposit policy stops paying |
| 14 | Review | Explain the model and the policy aloud in 3 minutes | |

## Week 3: Power BI, GitHub, interview
1. Open `powerbi/Hotel_Booking_Dashboard.pbip`, Refresh, and save as `.pbix`. Read every measure in `_Measures`.
2. Check that the cards match `outputs/INSIGHTS_REPORT.md`.
3. Export a PDF and take screenshots into `powerbi/screenshots/` (01_overview, 02_channels, 03_model, 04_forecast).
4. Push to GitHub, then practise `docs/RESUME_AND_INTERVIEW.md` aloud.

## Checklist
- [ ] I can explain leakage with an example from this data.
- [ ] I can explain why the split is by time.
- [ ] I can explain ROC-AUC to a manager in one sentence ("if I pick one cancelled and one kept booking at random, how often does the model rank the cancelled one riskier?").
- [ ] I can explain why the simple forecast won.
- [ ] I can walk through the overbooking formula in Excel.
- [ ] I know which numbers are assumptions.
