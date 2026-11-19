"""
STEP 5 - Weekly demand forecast: how many stays (non-cancelled arrivals) per week?

Methods, compared on the last 16 weeks of data (never used for fitting):
  1. Seasonal naive            = the same week last year (the benchmark every forecast must beat)
  2. Seasonal naive x growth   = same week last year x recent year-over-year growth
  3. Fourier regression        = linear trend + yearly sine/cosine seasonality + hotel mix,
                                 fitted with ridge regression (scikit-learn)
Metrics: MAE (stays per week) and MAPE (%).

Output: data/processed/forecast_weekly.csv, outputs/forecast_metrics.csv, figure 10.

Run:  python python/s05_demand_forecast.py
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

import config as C
from plot_style import plt, save, PRIMARY, ACCENT, NEUTRAL, NEGATIVE


def weekly_series() -> pd.DataFrame:
    d = pd.read_csv(C.PROCESSED_DIR / "fact_bookings.csv", parse_dates=["arrival_week_start"])
    stays = d[d["is_canceled"] == 0]
    w = stays.groupby("arrival_week_start").size().rename("actual").to_frame()
    full = pd.date_range(w.index.min(), w.index.max(), freq="W-MON")
    w = w.reindex(full, fill_value=0)
    return w.iloc[1:-1]  # first and last weeks are partial (data starts Wed, ends Thu)


def fourier(index: pd.DatetimeIndex, t0: pd.Timestamp, k: int = 4) -> np.ndarray:
    t = ((index - t0).days / 7.0).to_numpy()
    cols = [t]
    for i in range(1, k + 1):
        cols += [np.sin(2 * np.pi * i * t / 52.18), np.cos(2 * np.pi * i * t / 52.18)]
    return np.column_stack(cols)


def mae(a, f):
    return float(np.mean(np.abs(a - f)))


def mape(a, f):
    return float(np.mean(np.abs(a - f) / a) * 100)


def run() -> dict:
    C.ensure_dirs()
    w = weekly_series()
    h = C.FORECAST_TEST_WEEKS
    train, test = w.iloc[:-h], w.iloc[-h:]
    t0 = w.index[0]

    last_year = w["actual"].shift(52)
    f_naive = last_year.loc[test.index].to_numpy(float)
    # growth = last 12 training weeks vs the same 12 weeks one year earlier
    recent = train.iloc[-12:]
    growth = recent["actual"].sum() / last_year.loc[recent.index].sum()
    f_growth = f_naive * growth
    ridge = Ridge(alpha=1.0).fit(fourier(train.index, t0), train["actual"])
    f_fourier = ridge.predict(fourier(test.index, t0))

    a = test["actual"].to_numpy(float)
    rows = [{"method": "Seasonal naive (same week last year)", "mae": mae(a, f_naive), "mape_pct": mape(a, f_naive)},
            {"method": f"Seasonal naive x YoY growth ({growth:.2f})", "mae": mae(a, f_growth), "mape_pct": mape(a, f_growth)},
            {"method": "Fourier regression (trend + seasonality)", "mae": mae(a, f_fourier), "mape_pct": mape(a, f_fourier)}]
    met = pd.DataFrame(rows).round(2)
    met.to_csv(C.OUTPUT_DIR / "forecast_metrics.csv", index=False)
    print(met.to_string(index=False))
    best = met.sort_values("mape_pct").iloc[0]

    out = w.reset_index().rename(columns={"index": "week_start"})
    out["is_test"] = out["week_start"].isin(test.index).astype(int)
    for name, f in [("forecast_seasonal_naive", f_naive), ("forecast_naive_growth", f_growth),
                    ("forecast_fourier", f_fourier)]:
        out[name] = np.nan
        out.loc[out["is_test"] == 1, name] = np.round(f, 1)
    out["fitted_fourier"] = np.round(ridge.predict(fourier(w.index, t0)), 1)
    out["week_start"] = out["week_start"].dt.strftime("%Y-%m-%d")
    out.to_csv(C.PROCESSED_DIR / "forecast_weekly.csv", index=False, lineterminator="\n")

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(w.index, w["actual"], color=NEUTRAL, label="Actual stays per week")
    ax.plot(test.index, f_naive, color=NEGATIVE, ls=":", label="Seasonal naive")
    ax.plot(test.index, f_growth, color=ACCENT, label="Seasonal naive x growth")
    ax.plot(test.index, f_fourier, color=PRIMARY, label="Fourier regression")
    ax.axvline(test.index[0], color="#CBD5E1", ls="--")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(f"Weekly stays: forecasts for the last {h} weeks (held out)")
    save(fig, C.FIGURE_DIR / "10_weekly_forecast.png")

    return {"forecast_weeks_total": len(w), "forecast_test_weeks": h,
            "forecast_best_method": best["method"], "forecast_best_mape": float(best["mape_pct"]),
            "forecast_naive_mape": float(met.iloc[0]["mape_pct"]),
            "forecast_growth_factor": round(float(growth), 3),
            "avg_weekly_stays_test": round(float(a.mean()), 0)}


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:28s} {v}")
