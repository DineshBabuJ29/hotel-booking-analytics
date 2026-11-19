"""Central configuration: paths and settings shared by every script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "hotels.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "hotels.db"
SQL_DIR = ROOT / "sql"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
SQL_RESULT_DIR = OUTPUT_DIR / "sql_results"
EXCEL_DIR = ROOT / "excel"

# Cancellation model: train on earlier arrivals, test on the most recent 6 months (never seen in training).
MODEL_TEST_START = "2017-03-01"
# Forecast: hold out the last 16 weeks.
FORECAST_TEST_WEEKS = 16
RANDOM_STATE = 42

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# ISO-3 country code -> name for the countries that matter (top ~40 by bookings).
COUNTRY_NAMES = {
    "PRT": "Portugal", "GBR": "United Kingdom", "FRA": "France", "ESP": "Spain", "DEU": "Germany",
    "ITA": "Italy", "IRL": "Ireland", "BEL": "Belgium", "BRA": "Brazil", "NLD": "Netherlands",
    "USA": "United States", "CHE": "Switzerland", "CHN": "China", "AUT": "Austria", "SWE": "Sweden",
    "POL": "Poland", "ISR": "Israel", "RUS": "Russia", "NOR": "Norway", "ROU": "Romania",
    "FIN": "Finland", "DNK": "Denmark", "AUS": "Australia", "AGO": "Angola", "LUX": "Luxembourg",
    "MAR": "Morocco", "TUR": "Turkey", "HUN": "Hungary", "ARG": "Argentina", "JPN": "Japan",
    "CZE": "Czechia", "IND": "India", "KOR": "South Korea", "GRC": "Greece", "DZA": "Algeria",
    "SRB": "Serbia", "HRV": "Croatia", "MEX": "Mexico", "EST": "Estonia", "IRN": "Iran",
    "CAN": "Canada", "ZAF": "South Africa", "LTU": "Lithuania", "BGR": "Bulgaria", "NZL": "New Zealand",
}


def ensure_dirs() -> None:
    for d in (PROCESSED_DIR, OUTPUT_DIR, FIGURE_DIR, SQL_RESULT_DIR, EXCEL_DIR):
        d.mkdir(parents=True, exist_ok=True)
