"""
Generate the Power BI Project (.pbip) for the hotel dashboard.

    python powerbi/build_pbip.py      (close Power BI Desktop first)

Writes powerbi/Hotel_Booking_Dashboard.pbip + .SemanticModel/ + .Report/.
Open the .pbip in Power BI Desktop, click Refresh, then File > Save As .pbix.
"""
import json
import shutil
import sys
import uuid
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "python"))
import config as C  # noqa: E402

NAME = "Hotel_Booking_Dashboard"
SM_DIR, RPT_DIR = HERE / f"{NAME}.SemanticModel", HERE / f"{NAME}.Report"
M = "_Measures"

TABLES = ["fact_bookings", "dim_country", "model_deciles", "model_importance", "model_metrics", "forecast_weekly"]
TEXT_COLS = {"country", "arrival_month", "lead_time_bucket", "feature", "model"}
# week_start is a real date so the forecast chart gets a continuous time axis (no scrolling)
DATE_COLS = {"arrival_date", "booking_date", "reservation_status_date", "arrival_week_start", "week_start"}

# --------------------------------------------------------------------------- #
# Semantic model
# --------------------------------------------------------------------------- #
def column_types(table):
    df = pd.read_csv(C.PROCESSED_DIR / f"{table}.csv", low_memory=False)
    out = []
    for col in df.columns:
        s = df[col]
        if col in DATE_COLS:
            out.append((col, "dateTime", "type date"))
        elif col in TEXT_COLS or s.dtype == object:
            out.append((col, "string", "type text"))
        elif pd.api.types.is_integer_dtype(s) or (s.dropna() % 1 == 0).all():
            out.append((col, "int64", "Int64.Type"))
        else:
            out.append((col, "double", "type number"))
    return out


def csv_partition(table, types):
    tl = ", ".join(f'{{"{c}", {m}}}' for c, _, m in types)
    return ["let",
            f'    Source = Csv.Document(File.Contents(DataFolder & "{table}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
            "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
            '    Blanks = Table.TransformColumns(Promoted, {}, each if _ = "" then null else _),',
            f'    Typed = Table.TransformColumnTypes(Blanks, {{{tl}}}, "en-US")',
            "in", "    Typed"]


DATE_M = ["let",
          "    StartDate = #date(2015, 7, 1), EndDate = #date(2017, 8, 31),",
          "    Dates = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),",
          '    T0 = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),',
          '    T1 = Table.TransformColumnTypes(T0, {{"Date", type date}}),',
          '    T2 = Table.AddColumn(T1, "Year", each Date.Year([Date]), Int64.Type),',
          '    T3 = Table.AddColumn(T2, "Month Num", each Date.Month([Date]), Int64.Type),',
          '    T4 = Table.AddColumn(T3, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),',
          '    T5 = Table.AddColumn(T4, "Year Month", each Date.ToText([Date], "yyyy-MM", "en-US"), type text),',
          '    T6 = Table.AddColumn(T5, "Quarter", each Text.From(Date.Year([Date])) & "-Q" & Text.From(Date.QuarterOfYear([Date])), type text)',
          "in", "    T6"]
DATE_COLUMNS = [("Date", "dateTime"), ("Year", "int64"), ("Month Num", "int64"), ("Month", "string"),
                ("Year Month", "string"), ("Quarter", "string")]

EUR, EUR2, PCT = '"€"#,0', '"€"#,0.00', "0.0%"
B = "fact_bookings"
MEASURES = [
    # Bookings & revenue
    ("Bookings", f"COUNTROWS ( {B} )", "#,0", "Bookings & Revenue"),
    ("Cancellations", f"SUM ( {B}[is_canceled] )", "#,0", "Bookings & Revenue"),
    ("Cancel Rate %", "DIVIDE ( [Cancellations], [Bookings] )", PCT, "Bookings & Revenue"),
    ("Booked Value", f"SUM ( {B}[booking_value] )", EUR, "Bookings & Revenue"),
    ("Realized Revenue", f"SUM ( {B}[realized_revenue] )", EUR, "Bookings & Revenue"),
    ("Lost Revenue", f"SUM ( {B}[lost_revenue] )", EUR, "Bookings & Revenue"),
    ("Revenue Kept %", "DIVIDE ( [Realized Revenue], [Booked Value] )", PCT, "Bookings & Revenue"),
    ("Stayed Room Nights", f"CALCULATE ( SUM ( {B}[room_nights] ), {B}[is_canceled] = 0 )", "#,0", "Bookings & Revenue"),
    ("Realized ADR",
     f"DIVIDE (\n    CALCULATE ( SUM ( {B}[booking_value] ), {B}[is_canceled] = 0, {B}[is_paid_stay] = 1 ),\n"
     f"    CALCULATE ( SUM ( {B}[room_nights] ), {B}[is_canceled] = 0, {B}[is_paid_stay] = 1 )\n)", EUR2, "Bookings & Revenue"),
    ("Avg Stay Nights", f"CALCULATE ( AVERAGE ( {B}[room_nights] ), {B}[is_canceled] = 0 )", "0.00", "Bookings & Revenue"),
    ("Avg Lead Time Days", f"AVERAGE ( {B}[lead_time] )", "0", "Bookings & Revenue"),
    ("Online Share %", f"DIVIDE ( CALCULATE ( [Bookings], {B}[is_online_ta] = 1 ), [Bookings] )", PCT, "Bookings & Revenue"),
    ("Repeat Guest %", f"AVERAGE ( {B}[is_repeated_guest] )", PCT, "Bookings & Revenue"),
    ("Realized Revenue PY", "CALCULATE ( [Realized Revenue], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", EUR, "Bookings & Revenue"),
    ("Realized Revenue YoY %", "DIVIDE ( [Realized Revenue] - [Realized Revenue PY], [Realized Revenue PY] )", PCT, "Bookings & Revenue"),
    # Model
    ("Model AUC (Gradient Boosting)", 'CALCULATE ( MAX ( model_metrics[roc_auc] ), model_metrics[model] = "Gradient boosting" )', "0.000", "Model"),
    ("Model AUC (Logistic)", 'CALCULATE ( MAX ( model_metrics[roc_auc] ), model_metrics[model] = "Logistic regression" )', "0.000", "Model"),
    ("Model AUC No-Deposit", 'CALCULATE ( MAX ( model_metrics[roc_auc_no_deposit] ), model_metrics[model] = "Gradient boosting" )', "0.000", "Model"),
    ("Decile Actual Cancel %", "DIVIDE ( SUM ( model_deciles[cancellations] ), SUM ( model_deciles[bookings] ) )", PCT, "Model"),
    ("Decile Predicted Cancel %", "DIVIDE ( SUMX ( model_deciles, model_deciles[avg_predicted] * model_deciles[bookings] ), SUM ( model_deciles[bookings] ) )", PCT, "Model"),
    ("Decile Share of Cancellations", "DIVIDE ( SUM ( model_deciles[cancellations] ), CALCULATE ( SUM ( model_deciles[cancellations] ), ALL ( model_deciles ) ) )", PCT, "Model"),
    ("Top Decile Cancel %", "CALCULATE ( [Decile Actual Cancel %], model_deciles[risk_decile] = 1 )", PCT, "Model"),
    ("Top Decile Share of Cancellations", "CALCULATE ( [Decile Share of Cancellations], model_deciles[risk_decile] = 1 )", PCT, "Model"),
    ("Deposit Value Protected (1 night)", "SUM ( model_deciles[first_night_value_of_cancellations] )", EUR, "Model"),
    ("Decile Lost Revenue", "SUM ( model_deciles[lost_revenue] )", EUR, "Model"),
    ("Feature Importance (AUC drop)", "SUM ( model_importance[auc_drop] )", "0.000", "Model"),
    # Forecast
    ("Actual Stays", "SUM ( forecast_weekly[actual] )", "#,0", "Forecast"),
    ("Forecast Seasonal Naive", "SUM ( forecast_weekly[forecast_seasonal_naive] )", "#,0", "Forecast"),
    ("Forecast Fourier", "SUM ( forecast_weekly[forecast_fourier] )", "#,0", "Forecast"),
    ("MAPE Seasonal Naive",
     "AVERAGEX ( FILTER ( forecast_weekly, forecast_weekly[is_test] = 1 ),\n"
     "    ABS ( forecast_weekly[actual] - forecast_weekly[forecast_seasonal_naive] ) / forecast_weekly[actual] )", PCT, "Forecast"),
    ("MAPE Fourier",
     "AVERAGEX ( FILTER ( forecast_weekly, forecast_weekly[is_test] = 1 ),\n"
     "    ABS ( forecast_weekly[actual] - forecast_weekly[forecast_fourier] ) / forecast_weekly[actual] )", PCT, "Forecast"),
    ("Avg Weekly Stays (test)", "CALCULATE ( AVERAGE ( forecast_weekly[actual] ), forecast_weekly[is_test] = 1 )", "#,0", "Forecast"),
]
RELATIONSHIPS = [(B, "arrival_date", "Date", "Date"), (B, "country", "dim_country", "country")]


def uid():
    return str(uuid.uuid4())


def build_model():
    tables = []
    for t in TABLES:
        types = column_types(t)
        tables.append({"name": t, "lineageTag": uid(),
                       "columns": [{"name": c, "dataType": d, "sourceColumn": c, "summarizeBy": "none", "lineageTag": uid(),
                                    **({"formatString": "yyyy-mm-dd"} if c in DATE_COLS else {})} for c, d, _ in types],
                       "partitions": [{"name": t, "mode": "import", "source": {"type": "m", "expression": csv_partition(t, types)}}]})
    dcols = []
    for c, d in DATE_COLUMNS:
        col = {"name": c, "dataType": d, "sourceColumn": c, "summarizeBy": "none", "lineageTag": uid()}
        if c == "Date":
            col.update({"isKey": True, "formatString": "yyyy-mm-dd"})
        if c == "Month":
            col["sortByColumn"] = "Month Num"
        dcols.append(col)
    tables.append({"name": "Date", "dataCategory": "Time", "lineageTag": uid(), "columns": dcols,
                   "partitions": [{"name": "Date", "mode": "import", "source": {"type": "m", "expression": DATE_M}}]})
    tables.append({"name": M, "lineageTag": uid(),
                   "columns": [{"name": "Placeholder", "dataType": "string", "sourceColumn": "Placeholder",
                                "isHidden": True, "summarizeBy": "none", "lineageTag": uid()}],
                   "partitions": [{"name": M, "mode": "import", "source": {"type": "m", "expression": [
                       "let", "    Source = #table(type table [Placeholder = text], {})", "in", "    Source"]}}],
                   "measures": [{"name": n, "expression": dax.split("\n") if "\n" in dax else dax,
                                 "displayFolder": f, "lineageTag": uid(), **({"formatString": fmt} if fmt else {})}
                                for n, dax, fmt, f in MEASURES]})
    return {"compatibilityLevel": 1567, "model": {
        "culture": "en-US", "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
        "defaultPowerBIDataSourceVersion": "powerBI_V3", "sourceQueryCulture": "en-US",
        "tables": tables,
        "relationships": [{"name": uid(), "fromTable": a, "fromColumn": b, "toTable": c, "toColumn": d}
                          for a, b, c, d in RELATIONSHIPS],
        "expressions": [{"name": "DataFolder", "kind": "m", "lineageTag": uid(),
                         "expression": f'"{C.PROCESSED_DIR}\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'}],
        "annotations": [{"name": "PBI_QueryOrder", "value": json.dumps(["DataFolder"] + TABLES + ["Date", M])},
                        {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                        {"name": "PBIDesktopVersion", "value": "2.149.1054.0"}]}}


# --------------------------------------------------------------------------- #
# Report engine (same as the Olist project)
# --------------------------------------------------------------------------- #
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def col(t, n):
    return ("col", t, n)


def mea(n):
    return ("mea", M, n)


def qref(f):
    return f"{f[1]}.{f[2]}"


def fexpr(f, alias):
    return {("Column" if f[0] == "col" else "Measure"): {"Expression": {"SourceRef": {"Source": alias}}, "Property": f[2]}}


class Page:
    def __init__(self, name, ordinal):
        self.name, self.ordinal, self.visuals, self.z = name, ordinal, [], 0

    def add(self, vtype, x, y, w, h, roles=None, title=None, sort=None, objects=None, extra_vc=None):
        self.z += 1000
        sv = {"visualType": vtype, "drillFilterOtherVisuals": True}
        if roles:
            aliases, frm = {}, []
            for fs in roles.values():
                for f in fs:
                    if f[1] not in aliases:
                        aliases[f[1]] = f"t{len(aliases)}"
                        frm.append({"Name": aliases[f[1]], "Entity": f[1], "Type": 0})
            sel, seen = [], set()
            for fs in roles.values():
                for f in fs:
                    if qref(f) not in seen:
                        seen.add(qref(f))
                        e = fexpr(f, aliases[f[1]])
                        e.update({"Name": qref(f), "NativeReferenceName": f[2]})
                        sel.append(e)
            act = lambda i, r, f: i == 0 and f[0] == "col" and (r in ("Category", "Rows") or vtype == "slicer")
            sv["projections"] = {r: [{"queryRef": qref(f), **({"active": True} if act(i, r, f) else {})}
                                     for i, f in enumerate(fs)] for r, fs in roles.items()}
            pq = {"Version": 2, "From": frm, "Select": sel}
            if sort:
                f, dirn = sort
                pq["OrderBy"] = [{"Direction": 1 if dirn == "asc" else 2, "Expression": fexpr(f, aliases[f[1]])}]
                sv["hasDefaultSort"] = True
            sv["prototypeQuery"] = pq
        if objects:
            sv["objects"] = objects
        vc = {}
        if title:
            vc["title"] = [{"properties": {"show": lit(True), "text": lit(title), "fontSize": lit(11)}}]
        if extra_vc:
            vc.update(extra_vc)
        if vc:
            sv["vcObjects"] = vc
        cfg = {"name": uuid.uuid4().hex[:20], "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": self.z,
               "width": w, "height": h, "tabOrder": self.z}}], "singleVisual": sv}
        self.visuals.append({"x": x, "y": y, "z": self.z, "width": w, "height": h,
                             "config": json.dumps(cfg), "filters": "[]", "tabOrder": self.z})

    def header(self, title, subtitle):
        obj = {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "20pt", "color": "#134E4A"}}]},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "color": "#475569"}}]}]}}]}
        self.add("textbox", 16, 4, 820, 62, objects=obj,
                 extra_vc={"background": [{"properties": {"show": lit(False)}}], "border": [{"properties": {"show": lit(False)}}]})

    def slicer(self, field, x, title, w=200):
        self.add("slicer", x, 8, w, 56, roles={"Values": [field]},
                 objects={"data": [{"properties": {"mode": lit("Dropdown")}}], "header": [{"properties": {"text": lit(title)}}]})

    def cards(self, names, y=74, h=88):
        gap, n = 12, len(names)
        w = (1280 - 32 - gap * (n - 1)) // n
        for i, nm in enumerate(names):
            self.add("card", 16 + i * (w + gap), y, w, h, roles={"Values": [mea(nm)]},
                     objects={"labels": [{"properties": {"fontSize": lit(22)}}],
                              "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(10)}}]})

    def section(self):
        return {"name": uuid.uuid4().hex[:20], "displayName": self.name, "displayOption": 1, "width": 1280,
                "height": 720, "ordinal": self.ordinal, "filters": "[]", "config": "{}", "visualContainers": self.visuals}


LABELS = {"labels": [{"properties": {"show": lit(True)}}]}


def table_style(widths):
    return {"columnWidth": [{"properties": {"value": lit(px)}, "selector": {"metadata": qref(f)}} for f, px in widths.items()],
            "values": [{"properties": {"fontSize": lit(9)}}],
            "columnHeaders": [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}],
            "total": [{"properties": {"fontSize": lit(9)}}]}


def pages():
    ym, hotel = col("Date", "Year Month"), col(B, "hotel")
    out = []

    p = Page("Overview", 0)
    p.header("Hotel Booking Demand | Overview",
             "119k bookings, City & Resort hotel, Portugal, Jul 2015 - Aug 2017. Revenue = ADR x nights (EUR).")
    p.slicer(hotel, 860, "Hotel")
    p.slicer(col("Date", "Year"), 1070, "Arrival year")
    p.cards(["Bookings", "Cancel Rate %", "Realized Revenue", "Lost Revenue", "Realized ADR", "Avg Stay Nights"])
    p.add("lineClusteredColumnComboChart", 16, 174, 800, 270,
          roles={"Category": [ym], "Y": [mea("Realized Revenue")], "Y2": [mea("Cancel Rate %")]},
          title="Monthly realized revenue (columns) and cancellation rate (line)", sort=(ym, "asc"))
    p.add("lineChart", 828, 174, 436, 270,
          roles={"Category": [col("Date", "Month")], "Y": [mea("Realized ADR")], "Series": [hotel]},
          title="Price (realized ADR) by month: resort peaks in summer", sort=(col("Date", "Month"), "asc"))
    p.add("barChart", 16, 456, 500, 252,
          roles={"Category": [col(B, "channel_group")], "Y": [mea("Lost Revenue")]},
          title="Revenue lost to cancellations, by channel", sort=(mea("Lost Revenue"), "desc"), objects=LABELS)
    p.add("columnChart", 528, 456, 736, 252,
          roles={"Category": [col(B, "lead_time_bucket")], "Y": [mea("Cancel Rate %")]},
          title="Cancellation rate by booking lead time", sort=(col(B, "lead_time_bucket"), "asc"), objects=LABELS)
    out.append(p)

    p = Page("Channels & Pricing", 1)
    p.header("Distribution Channels & Pricing",
             "Online travel agencies (OTA) are the largest channel, but keep the least of what they book.")
    p.slicer(hotel, 1070, "Hotel")
    p.cards(["Online Share %", "Revenue Kept %", "Realized ADR", "Avg Lead Time Days", "Repeat Guest %"])
    ch_cols = {col(B, "channel_group"): 150, mea("Bookings"): 62, mea("Cancel Rate %"): 60, mea("Realized ADR"): 66,
               mea("Realized Revenue"): 92, mea("Revenue Kept %"): 62, mea("Avg Lead Time Days"): 62}
    p.add("tableEx", 16, 174, 640, 250, roles={"Values": list(ch_cols)}, title="Channel economics",
          sort=(mea("Realized Revenue"), "desc"), objects=table_style(ch_cols))
    p.add("barChart", 668, 174, 596, 250,
          roles={"Category": [col(B, "channel_group")], "Y": [mea("Revenue Kept %")]},
          title="Share of booked value actually earned, by channel", sort=(mea("Revenue Kept %"), "desc"), objects=LABELS)
    p.add("lineChart", 16, 436, 560, 272, roles={"Category": [col("Date", "Quarter")], "Y": [mea("Online Share %")]},
          title="Online travel agency share of bookings, by quarter", sort=(col("Date", "Quarter"), "asc"), objects=LABELS)
    cty = {col("dim_country", "country_name"): 130, mea("Bookings"): 70, mea("Realized Revenue"): 100,
           mea("Cancel Rate %"): 75, mea("Realized ADR"): 80}
    p.add("tableEx", 588, 436, 676, 272, roles={"Values": list(cty)}, title="Source countries",
          sort=(mea("Realized Revenue"), "desc"), objects=table_style(cty))
    out.append(p)

    p = Page("Cancellation Risk Model", 2)
    p.header("Cancellation Risk Model",
             "Gradient boosting, trained on arrivals before Mar-2017, tested on Mar-Aug 2017 (unseen). No-Deposit bookings.")
    p.cards(["Model AUC (Gradient Boosting)", "Model AUC (Logistic)", "Model AUC No-Deposit",
             "Top Decile Cancel %", "Top Decile Share of Cancellations"])
    dec = col("model_deciles", "risk_decile")
    p.add("clusteredColumnChart", 16, 174, 640, 270,
          roles={"Category": [dec], "Y": [mea("Decile Actual Cancel %"), mea("Decile Predicted Cancel %")]},
          title="Actual vs predicted cancellation rate by risk decile (1 = riskiest 10%)", sort=(dec, "asc"))
    p.add("barChart", 668, 174, 596, 270,
          roles={"Category": [col("model_importance", "feature")], "Y": [mea("Feature Importance (AUC drop)")]},
          title="What drives cancellation risk (drop in AUC when shuffled)",
          sort=(mea("Feature Importance (AUC drop)"), "desc"))
    dcols = {dec: 70, mea("Decile Actual Cancel %"): 90, mea("Decile Share of Cancellations"): 100,
             mea("Decile Lost Revenue"): 110, mea("Deposit Value Protected (1 night)"): 130}
    p.add("tableEx", 16, 456, 640, 252, roles={"Values": list(dcols)},
          title="Risk deciles: where a deposit policy would act", sort=(dec, "asc"), objects=table_style(dcols))
    note = {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": "How to read this page", "textStyle": {"fontWeight": "bold", "fontSize": "11pt"}}]},
        {"textRuns": [{"value": "Deciles rank No-Deposit bookings by predicted risk. The riskiest 10% cancel far more often "
                                "than average; asking only them for a one-night deposit protects revenue while leaving 90% "
                                "of guests untouched.", "textStyle": {"fontSize": "10pt"}}]},
        {"textRuns": [{"value": "Leakage excluded: reservation status, assigned room, booking changes, parking requests. "
                                "Predicted rates run low in the test months (cancellations rose), so use the ranking, and "
                                "recalibrate before using probabilities.", "textStyle": {"fontSize": "10pt", "color": "#475569"}}]},
    ]}}]}
    p.add("textbox", 668, 456, 596, 252, objects=note)
    out.append(p)

    p = Page("Demand Forecast & Guests", 3)
    p.header("Demand Forecast & Guest Behaviour",
             "Weekly stays (non-cancelled arrivals). Forecasts are scored on the last 16 weeks, held out.")
    p.cards(["Avg Weekly Stays (test)", "MAPE Seasonal Naive", "MAPE Fourier", "Repeat Guest %"])
    wk = col("forecast_weekly", "week_start")
    p.add("lineChart", 16, 174, 1248, 280,
          roles={"Category": [wk], "Y": [mea("Actual Stays"), mea("Forecast Seasonal Naive"), mea("Forecast Fourier")]},
          title="Weekly stays: actual vs forecasts (forecast lines cover the 16 held-out weeks)", sort=(wk, "asc"))
    p.add("columnChart", 16, 466, 400, 242,
          roles={"Category": [col(B, "total_of_special_requests")], "Y": [mea("Cancel Rate %")]},
          title="Cancellation rate by number of special requests",
          sort=(col(B, "total_of_special_requests"), "asc"), objects=LABELS)
    p.add("columnChart", 428, 466, 400, 242,
          roles={"Category": [col(B, "customer_type")], "Y": [mea("Cancel Rate %")]},
          title="Cancellation rate by customer type", sort=(mea("Cancel Rate %"), "desc"), objects=LABELS)
    p.add("columnChart", 840, 466, 424, 242,
          roles={"Category": [col(B, "deposit_type")], "Y": [mea("Cancel Rate %")]},
          title="Deposit type: the 'Non Refund' anomaly", sort=(mea("Cancel Rate %"), "desc"), objects=LABELS)
    out.append(p)
    return out


def build_report():
    theme = "HotelTheme.json"
    ver = {"visual": "2.4.0", "report": "3.0.0", "page": "2.3.0"}
    cfg = {"version": "5.68", "themeCollection": {"baseTheme": {"name": "CY25SU11", "version": ver, "type": 2},
                                                  "customTheme": {"name": theme, "reportVersionAtImport": ver, "type": 1}},
           "activeSectionIndex": 0, "defaultDrillFilterOtherVisuals": True,
           "settings": {"useNewFilterPaneExperience": True, "allowChangeFilterTypes": True,
                        "useStylableVisualContainerHeader": True, "exportDataMode": 1, "useEnhancedTooltips": True}}
    return {"config": json.dumps(cfg), "layoutOptimization": 0,
            "resourcePackages": [
                {"resourcePackage": {"name": "SharedResources", "type": 2, "disabled": False,
                                     "items": [{"type": 202, "path": "BaseThemes/CY25SU11.json", "name": "CY25SU11"}]}},
                {"resourcePackage": {"name": "RegisteredResources", "type": 1, "disabled": False,
                                     "items": [{"type": 201, "path": theme, "name": theme}]}}],
            "sections": [p.section() for p in pages()]}, theme


def wj(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    for d in (SM_DIR, RPT_DIR):
        if d.exists():
            shutil.rmtree(d)
    wj(SM_DIR / "definition.pbism", {"version": "1.0", "settings": {}})
    wj(SM_DIR / "model.bim", build_model())
    rep, theme = build_report()
    wj(RPT_DIR / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    wj(RPT_DIR / "report.json", rep)
    shutil.copytree(HERE / "_template" / "SharedResources", RPT_DIR / "StaticResources" / "SharedResources")
    th = json.loads((HERE / "hotel_theme.json").read_text(encoding="utf-8"))
    th["name"] = theme
    wj(RPT_DIR / "StaticResources" / "RegisteredResources" / theme, th)
    wj(HERE / f"{NAME}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                               "settings": {"enableAutoRecovery": True}})
    (HERE / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    n = sum(len(s["visualContainers"]) for s in rep["sections"])
    print(f"Wrote {NAME}.pbip: {len(TABLES) + 2} tables, {len(MEASURES)} measures, "
          f"{len(RELATIONSHIPS)} relationships, {len(rep['sections'])} pages, {n} visuals")


if __name__ == "__main__":
    main()
