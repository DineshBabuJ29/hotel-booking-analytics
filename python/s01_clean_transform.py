"""
STEP 1 - Data quality audit, cleaning and feature engineering.

Input : data/raw/hotels.csv (119,390 bookings, 32 columns)
Output: data/processed/fact_bookings.csv   one row per booking, clean + derived fields
        data/processed/dim_country.csv     country code -> name
        outputs/data_quality_report.csv

Business definitions (same in SQL, Python and DAX, see docs/DATA_DICTIONARY.md):
  * room_nights      = weekend nights + week nights
  * booking_value    = ADR x room_nights (what the stay is worth when booked)
  * realized_revenue = booking_value of bookings that were NOT canceled
  * lost_revenue     = booking_value of canceled bookings (incl. no-shows)
  * Online share     = market_segment 'Online TA' (Booking.com, Expedia ...)

Run:  python python/s01_clean_transform.py
"""
import numpy as np
import pandas as pd

import config as C


def audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append({"column": col, "dtype": str(s.dtype), "nulls": int(s.isna().sum()),
                     "null_text": int((s.astype(str).str.upper() == "NULL").sum()),
                     "distinct": int(s.nunique(dropna=True))})
    rep = pd.DataFrame(rows)
    rep.to_csv(C.OUTPUT_DIR / "data_quality_report.csv", index=False)
    return rep


def clean(df: pd.DataFrame, issues: dict) -> pd.DataFrame:
    d = df.copy()
    n0 = len(d)

    # --- Exact duplicate rows ------------------------------------------------ #
    # The file has no booking ID, so identical rows cannot be proven to be errors:
    # a group of rooms booked together produces identical rows. We KEEP them and
    # report a sensitivity check (s05) showing the main results without them.
    d["is_exact_duplicate"] = d.duplicated(keep="first").astype(int)
    issues["exact_duplicate_rows_kept_and_flagged"] = int(d["is_exact_duplicate"].sum())

    # --- Invalid rows (removed) --------------------------------------------- #
    guests = d["adults"] + d["children"].fillna(0) + d["babies"]
    bad = {
        "removed_zero_guests": guests == 0,
        "removed_negative_adr": d["adr"] < 0,
        "removed_adr_outlier_over_1000": d["adr"] > 1000,
        "removed_undefined_channel": (d["distribution_channel"] == "Undefined") | (d["market_segment"] == "Undefined"),
    }
    drop = pd.Series(False, index=d.index)
    for k, m in bad.items():
        issues[k] = int((m & ~drop).sum())
        drop |= m
    d = d[~drop].copy()
    issues["rows_removed_total"] = n0 - len(d)

    # --- Fixes ------------------------------------------------------------- #
    issues["children_missing_set_0"] = int(d["children"].isna().sum())
    d["children"] = d["children"].fillna(0).astype(int)
    d["country"] = d["country"].replace({"CN": "CHN"}).fillna("UNK")   # 'CN' is not ISO-3
    issues["country_missing_set_UNK"] = int((d["country"] == "UNK").sum())
    d["meal"] = d["meal"].replace({"Undefined": "SC"})                 # dataset docs: Undefined = SC (no meal)
    d["agent"] = d["agent"].fillna(0).astype(int)                      # 0 = no travel agent
    d["company"] = d["company"].fillna(0).astype(int)

    # --- Dates --------------------------------------------------------------- #
    month_num = d["arrival_date_month"].map({m: i + 1 for i, m in enumerate(C.MONTHS)})
    d["arrival_date"] = pd.to_datetime(dict(year=d["arrival_date_year"], month=month_num,
                                            day=d["arrival_date_day_of_month"]))
    d["booking_date"] = d["arrival_date"] - pd.to_timedelta(d["lead_time"], unit="D")
    d["arrival_month"] = d["arrival_date"].dt.strftime("%Y-%m")
    d["arrival_month_num"] = month_num
    d["arrival_month_name"] = d["arrival_date"].dt.strftime("%b")
    d["arrival_week_start"] = (d["arrival_date"] - pd.to_timedelta(d["arrival_date"].dt.dayofweek, unit="D"))
    d["arrival_weekday"] = d["arrival_date"].dt.day_name().str[:3]
    d["season"] = d["arrival_month_num"].map(
        {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
         6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"})

    # --- Stay, guests, money ---------------------------------------------- #
    d["room_nights"] = d["stays_in_weekend_nights"] + d["stays_in_week_nights"]
    d["is_day_use"] = (d["room_nights"] == 0).astype(int)
    d["guests"] = d["adults"] + d["children"] + d["babies"]
    d["is_family"] = ((d["children"] + d["babies"]) > 0).astype(int)
    d["booking_value"] = (d["adr"] * d["room_nights"]).round(2)
    d["realized_revenue"] = np.where(d["is_canceled"] == 0, d["booking_value"], 0).round(2)
    d["lost_revenue"] = np.where(d["is_canceled"] == 1, d["booking_value"], 0).round(2)
    d["is_paid_stay"] = ((d["adr"] > 0) & (d["room_nights"] > 0)).astype(int)  # for price (ADR) analysis

    d["is_online_ta"] = (d["market_segment"] == "Online TA").astype(int)
    d["channel_group"] = d["market_segment"].map({
        "Online TA": "Online travel agency", "Offline TA/TO": "Offline agency / tour operator",
        "Direct": "Direct", "Groups": "Groups", "Corporate": "Corporate",
        "Complementary": "Other", "Aviation": "Other"})
    d["lead_time_bucket"] = pd.cut(d["lead_time"], [-1, 7, 30, 90, 180, 365, 10_000],
                                   labels=["1. 0-7 days", "2. 8-30 days", "3. 31-90 days",
                                           "4. 91-180 days", "5. 181-365 days", "6. 365+ days"]).astype(str)
    d["is_room_upgrade_or_change"] = (d["reserved_room_type"] != d["assigned_room_type"]).astype(int)
    d["has_special_requests"] = (d["total_of_special_requests"] > 0).astype(int)
    d["is_no_show"] = (d["reservation_status"] == "No-Show").astype(int)

    d.insert(0, "booking_id", np.arange(1, len(d) + 1))  # surrogate key (the raw file has none)
    for col in ["arrival_date", "booking_date", "arrival_week_start"]:
        d[col] = d[col].dt.strftime("%Y-%m-%d")
    return d


def run() -> dict:
    C.ensure_dirs()
    raw = pd.read_csv(C.RAW_FILE)
    audit(raw)
    issues = {}
    d = clean(raw, issues)
    d.to_csv(C.PROCESSED_DIR / "fact_bookings.csv", index=False, lineterminator="\n")

    countries = (d.groupby("country").size().rename("bookings").reset_index()
                 .assign(country_name=lambda x: x["country"].map(C.COUNTRY_NAMES).fillna(x["country"])))
    countries["is_domestic"] = (countries["country"] == "PRT").astype(int)
    countries.to_csv(C.PROCESSED_DIR / "dim_country.csv", index=False, lineterminator="\n")

    print(f"Raw rows: {len(raw):,}   Clean rows: {len(d):,}")
    print("\nCLEANING ISSUES HANDLED")
    for k, v in issues.items():
        print(f"  {k:42s} {v:>8,}")
    return {"raw_rows": len(raw), "clean_rows": len(d), "cleaning_issues": issues,
            "first_arrival": d["arrival_date"].min(), "last_arrival": d["arrival_date"].max()}


if __name__ == "__main__":
    run()
