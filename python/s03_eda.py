"""
STEP 3 - Exploratory analysis in pandas + charts (outputs/figures/).
Same questions as the SQL files, answered in Python, plus the numbers for the report.

Run:  python python/s03_eda.py
"""
import numpy as np
import pandas as pd

import config as C
from plot_style import plt, money, pct, save, PRIMARY, ACCENT, NEGATIVE, NEUTRAL


def load():
    return pd.read_csv(C.PROCESSED_DIR / "fact_bookings.csv", parse_dates=["arrival_date"])


def realized_adr(df):
    s = df[(df["is_canceled"] == 0) & (df["is_paid_stay"] == 1)]
    return s["booking_value"].sum() / s["room_nights"].sum()


def run() -> dict:
    C.ensure_dirs()
    d = load()
    m = {}
    m["bookings"] = len(d)
    m["cancel_rate_pct"] = round(100 * d["is_canceled"].mean(), 1)
    m["realized_revenue"] = round(float(d["realized_revenue"].sum()), 0)
    m["lost_revenue"] = round(float(d["lost_revenue"].sum()), 0)
    m["lost_share_pct"] = round(100 * d["lost_revenue"].sum() / d["booking_value"].sum(), 1)
    m["realized_adr"] = round(float(realized_adr(d)), 2)
    for h, g in d.groupby("hotel"):
        key = "city" if h.startswith("City") else "resort"
        m[f"{key}_cancel_rate_pct"] = round(100 * g["is_canceled"].mean(), 1)
        m[f"{key}_realized_adr"] = round(float(realized_adr(g)), 2)
        m[f"{key}_avg_stay"] = round(float(g.loc[g["is_canceled"] == 0, "room_nights"].mean()), 2)

    print("Building charts ...")
    # 1. Monthly realized revenue by hotel
    mon = d.groupby(["arrival_month", "hotel"])["realized_revenue"].sum().unstack()
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for col, colr in zip(mon.columns, [PRIMARY, ACCENT]):
        ax.plot(mon.index, mon[col], marker="o", ms=3, label=col, color=colr)
    money(ax)
    ax.legend()
    ax.tick_params(axis="x", rotation=60)
    ax.set_title("Monthly realized revenue by hotel (Jul 2015 - Aug 2017)")
    save(fig, C.FIGURE_DIR / "01_monthly_revenue.png")

    # 2. Seasonality of price (ADR) vs cancellation
    s = d[(d["is_canceled"] == 0) & (d["is_paid_stay"] == 1)]
    adr_m = s.groupby(["arrival_month_num", "hotel"]).apply(
        lambda g: g["booking_value"].sum() / g["room_nights"].sum(), include_groups=False).unstack()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for col, colr in zip(adr_m.columns, [PRIMARY, ACCENT]):
        ax.plot(adr_m.index, adr_m[col], marker="o", label=col, color=colr)
    ax.set_xticks(range(1, 13), [x[:3] for x in C.MONTHS])
    money(ax)
    ax.legend()
    ax.set_title("Realized ADR (price per room-night) by month: resort peaks hard in summer")
    save(fig, C.FIGURE_DIR / "02_adr_seasonality.png")
    m["resort_adr_aug"] = round(float(adr_m.loc[8, "Resort Hotel"]), 2)
    m["resort_adr_jan"] = round(float(adr_m.loc[1, "Resort Hotel"]), 2)

    # 3. Channel economics
    ch = d.groupby("channel_group").agg(bookings=("booking_id", "size"), cancel=("is_canceled", "mean"),
                                        value=("booking_value", "sum"), realized=("realized_revenue", "sum"))
    ch["kept_pct"] = 100 * ch["realized"] / ch["value"]
    ch["share_bookings"] = 100 * ch["bookings"] / ch["bookings"].sum()
    ch["share_revenue"] = 100 * ch["realized"] / ch["realized"].sum()
    ch = ch.sort_values("realized", ascending=False)
    ch.round(2).to_csv(C.OUTPUT_DIR / "channel_summary.csv")
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.barh(ch.index[::-1], ch["kept_pct"][::-1], color=[PRIMARY if "Direct" in i else NEUTRAL for i in ch.index[::-1]])
    ax.bar_label(bars, fmt="%.0f%%")
    pct(ax, "x")
    ax.set_title("Share of booked value actually earned (after cancellations), by channel")
    save(fig, C.FIGURE_DIR / "03_channel_revenue_kept.png")
    ota, direct = ch.loc["Online travel agency"], ch.loc["Direct"]
    m.update({"ota_booking_share_pct": round(float(ota["share_bookings"]), 1),
              "ota_revenue_share_pct": round(float(ota["share_revenue"]), 1),
              "ota_cancel_pct": round(100 * float(ota["cancel"]), 1),
              "ota_kept_pct": round(float(ota["kept_pct"]), 1),
              "direct_cancel_pct": round(100 * float(direct["cancel"]), 1),
              "direct_kept_pct": round(float(direct["kept_pct"]), 1),
              "groups_cancel_pct": round(100 * float(ch.loc["Groups", "cancel"]), 1)})
    q = d.assign(q=d["arrival_date"].dt.to_period("Q")).groupby("q")["is_online_ta"].mean()
    m["online_share_first_q_pct"] = round(100 * float(q.iloc[0]), 1)
    m["online_share_last_q_pct"] = round(100 * float(q.iloc[-1]), 1)

    # 4. Lead time vs cancellation
    lt = d.groupby("lead_time_bucket").agg(cancel=("is_canceled", "mean"), n=("booking_id", "size"))
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar([i[3:] for i in lt.index], 100 * lt["cancel"], color=NEGATIVE)
    ax.bar_label(bars, fmt="%.0f%%")
    pct(ax)
    ax.set_title("Cancellation rate rises with lead time")
    ax.set_xlabel("Days between booking and arrival")
    save(fig, C.FIGURE_DIR / "04_cancel_by_lead_time.png")
    m["cancel_lead_0_7_pct"] = round(100 * float(lt["cancel"].iloc[0]), 1)
    m["cancel_lead_181_365_pct"] = round(100 * float(lt["cancel"].iloc[4]), 1)

    # 5. Cancellation drivers (No Deposit bookings only, to avoid the Non-Refund anomaly)
    nd = d[d["deposit_type"] == "No Deposit"]
    drivers = {
        "No special requests": nd.loc[nd["total_of_special_requests"] == 0, "is_canceled"].mean(),
        "1+ special requests": nd.loc[nd["total_of_special_requests"] > 0, "is_canceled"].mean(),
        "New guest": nd.loc[nd["is_repeated_guest"] == 0, "is_canceled"].mean(),
        "Repeat guest": nd.loc[nd["is_repeated_guest"] == 1, "is_canceled"].mean(),
        "Online TA": nd.loc[nd["is_online_ta"] == 1, "is_canceled"].mean(),
        "Direct": nd.loc[nd["market_segment"] == "Direct", "is_canceled"].mean(),
    }
    fig, ax = plt.subplots(figsize=(9, 4))
    names = list(drivers)[::-1]
    bars = ax.barh(names, [100 * drivers[k] for k in names],
                   color=[NEGATIVE if i % 2 else PRIMARY for i in range(len(names))])
    ax.bar_label(bars, fmt="%.0f%%")
    pct(ax, "x")
    ax.set_title("Cancellation rate by booking trait (No-Deposit bookings)")
    save(fig, C.FIGURE_DIR / "05_cancellation_drivers.png")
    m["cancel_no_requests_pct"] = round(100 * drivers["No special requests"], 1)
    m["cancel_with_requests_pct"] = round(100 * drivers["1+ special requests"], 1)
    m["cancel_repeat_pct"] = round(100 * drivers["Repeat guest"], 1)
    m["cancel_new_pct"] = round(100 * drivers["New guest"], 1)

    # 6. Countries: value vs reliability
    top = (d.groupby("country").agg(rev=("realized_revenue", "sum"), cancel=("is_canceled", "mean"),
                                    n=("booking_id", "size")).sort_values("rev", ascending=False).head(10))
    top.index = top.index.map(lambda c: C.COUNTRY_NAMES.get(c, c))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(100 * top["cancel"], top["rev"], s=top["n"] / 60, color=PRIMARY, alpha=.7)
    for name, r in top.iterrows():
        ax.annotate(name, (100 * r["cancel"], r["rev"]), xytext=(5, 3), textcoords="offset points", fontsize=8)
    money(ax)
    pct(ax, "x")
    ax.set_xlabel("Cancellation rate")
    ax.set_title("Top 10 source countries: revenue vs cancellation rate (bubble = bookings)")
    save(fig, C.FIGURE_DIR / "06_countries.png")
    m["portugal_cancel_pct"] = round(100 * float(top.loc["Portugal", "cancel"]), 1)
    m["portugal_revenue_share_pct"] = round(100 * float(top.loc["Portugal", "rev"] / d["realized_revenue"].sum()), 1)

    # 7. Deposit anomaly
    dep = d.groupby("deposit_type")["is_canceled"].agg(["mean", "size"])
    m["non_refund_cancel_pct"] = round(100 * float(dep.loc["Non Refund", "mean"]), 1)
    m["non_refund_bookings"] = int(dep.loc["Non Refund", "size"])
    m["no_deposit_cancel_pct"] = round(100 * float(dep.loc["No Deposit", "mean"]), 1)

    # 8. Sensitivity: results without exact duplicate rows
    u = d[d["is_exact_duplicate"] == 0]
    m["dedup_rows"] = len(u)
    m["dedup_cancel_rate_pct"] = round(100 * u["is_canceled"].mean(), 1)
    m["dedup_ota_cancel_pct"] = round(100 * u.loc[u["is_online_ta"] == 1, "is_canceled"].mean(), 1)
    m["dedup_direct_cancel_pct"] = round(100 * u.loc[u["market_segment"] == "Direct", "is_canceled"].mean(), 1)
    return m


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:32s} {v}")
