"""
STEP 2 - Load the clean tables into SQL and run every analysis query in /sql.

SQLite ships with Python, so every query is verified on each run. The SQL is
portable (CTEs, window functions, CASE; no vendor date functions), so it also runs
on MySQL 8. Load the same CSVs there with sql/01_schema_mysql.sql + 02_load_mysql.sql.

Output: data/hotels.db, outputs/sql_results/<file>_<query>.csv

Run:  python python/s02_build_database.py
"""
import re
import sqlite3

import pandas as pd

import config as C

TABLES = ["fact_bookings", "dim_country"]
ANALYSIS_FILES = ["03_data_quality.sql", "04_revenue_and_demand.sql",
                  "05_channels_and_pricing.sql", "06_cancellations_and_guests.sql"]


def split_queries(text: str):
    for stmt in text.split(";"):
        m = re.search(r"--\s*@name:\s*(\w+)", stmt)
        body = "\n".join(l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--"))
        if m and body.strip():
            yield m.group(1), body


def run() -> dict:
    C.ensure_dirs()
    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    con = sqlite3.connect(C.DB_PATH)
    try:
        for t in TABLES:
            df = pd.read_csv(C.PROCESSED_DIR / f"{t}.csv")
            df.to_sql(t, con, index=False)
            print(f"  loaded {t:15s} {len(df):>9,} rows")
        con.execute("CREATE INDEX ix_b_month ON fact_bookings(hotel, arrival_month)")
        con.execute("CREATE INDEX ix_b_country ON fact_bookings(country)")
        n = 0
        for fname in ANALYSIS_FILES:
            print(f"\n### {fname}")
            for name, sql in split_queries((C.SQL_DIR / fname).read_text(encoding="utf-8")):
                df = pd.read_sql_query(sql, con)
                df.to_csv(C.SQL_RESULT_DIR / f"{fname[:2]}_{name}.csv", index=False)
                n += 1
                print(f"\n-- {name} ({len(df)} rows)\n{df.head(10).to_string(index=False)}")
    finally:
        con.close()
    print(f"\n{n} queries ran OK")
    return {"sql_queries_run": n}


if __name__ == "__main__":
    run()
