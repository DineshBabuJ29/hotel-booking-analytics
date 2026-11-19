"""
STEP 6 - Build the Excel what-if model (excel/Hotel_Revenue_WhatIf.xlsx).

Three live-formula sheets. Yellow cells are inputs; change them and everything recalculates:
  1. Overbooking  - how many rooms to sell beyond capacity, using the binomial distribution
                    (BINOM.DIST) on the show-up probability. Finds the revenue-maximising level.
  2. Deposit      - deposit policy on the model's risk deciles: revenue protected vs guests lost.
  3. Channel mix  - what if a share of online-agency bookings moved to the direct channel?
Defaults come from the data; assumptions are labelled as such.

Run:  python python/s06_excel_whatif.py
"""
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from scipy.stats import binom

import config as C

INPUT = PatternFill("solid", fgColor="FEF3C7")
HEAD = PatternFill("solid", fgColor="1E3A8A")
OUT = PatternFill("solid", fgColor="DBEAFE")
WHITE_BOLD = Font(color="FFFFFF", bold=True)
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14, color="1E3A8A")
NOTE = Font(italic=True, size=9, color="475569")
THIN = Border(*(Side(style="thin", color="CBD5E1"),) * 4)
EUR = '"€"#,##0'
EUR2 = '"€"#,##0.00'
PCT = "0.0%"

MAX_OVERBOOK = 30
MAX_K = 260  # grid rows: supports capacity + overbooking up to 260 rooms


def header(ws, row, labels, col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.fill, c.font, c.alignment = HEAD, WHITE_BOLD, Alignment(horizontal="center", wrap_text=True)


def inp(ws, cell, value, fmt=None):
    ws[cell] = value
    ws[cell].fill, ws[cell].border = INPUT, THIN
    if fmt:
        ws[cell].number_format = fmt


def build_overbooking(wb, show_prob, adr):
    ws = wb.create_sheet("Overbooking")
    ws["A1"], ws["A1"].font = "Overbooking optimiser (one night, one hotel)", TITLE
    ws["A2"] = ("Sell (capacity + X) rooms. Each booking shows up with probability p. Revenue = ADR x rooms "
                "occupied; every guest who shows up to a full hotel is 'walked' (relocated) at a cost.")
    ws["A2"].font = NOTE
    rows = [("Rooms available (capacity)", 100, "0"),
            ("Probability a booking shows up (p)", round(show_prob, 3), PCT),
            ("Average daily rate (ADR)", round(adr, 2), EUR2),
            ("Cost of walking one guest (x ADR)", 2.0, "0.0"),
            ]
    for i, (lab, val, fmt) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=lab)
        inp(ws, f"B{i}", val, fmt)
    ws["C5"] = ("From data: City Hotel, No-Deposit, Mar-Aug 2017. Of bookings still on the books 3 days "
                "before arrival, the share that showed up (late cancellations + no-shows excluded)")
    ws["C6"] = "From data: City Hotel realized ADR"
    ws["C7"] = "Assumption: relocation + compensation + goodwill"
    for c in ("C5", "C6", "C7"):
        ws[c].font = NOTE

    # Results table: one column per overbooking level
    ws["A10"], ws["A10"].font = "Results by overbooking level", BOLD
    labels = ["Overbook by X rooms", "Rooms sold", "Expected rooms occupied", "Expected guests walked",
              "Expected room revenue", "Expected walk cost", "Expected net revenue", "Gain vs no overbooking"]
    for i, lab in enumerate(labels):
        ws.cell(row=11 + i, column=1, value=lab).font = BOLD
    grid_top = 25                      # probability grid starts here
    k_col = 1
    ws.cell(row=grid_top - 1, column=1, value="Probability grid: P(exactly k guests show up) for each X").font = BOLD
    ws.cell(row=grid_top, column=1, value="k").font = BOLD
    ws.cell(row=grid_top, column=2, value="min(k, capacity)").font = BOLD
    ws.cell(row=grid_top, column=3, value="max(k - capacity, 0)").font = BOLD
    first, last = grid_top + 1, grid_top + 1 + MAX_K
    for r in range(first, last + 1):
        ws.cell(row=r, column=1, value=r - first)
        ws.cell(row=r, column=2, value=f"=MIN(A{r},$B$4)")
        ws.cell(row=r, column=3, value=f"=MAX(A{r}-$B$4,0)")
    for x in range(MAX_OVERBOOK + 1):
        col = 4 + x
        L = get_column_letter(col)
        ws.cell(row=grid_top, column=col, value=f"X={x}").font = BOLD
        for r in range(first, last + 1):
            ws.cell(row=r, column=col,
                    # "_xlfn." is how the file format stores Excel 2010+ functions; Excel shows BINOM.DIST
                    value=f"=IF(A{r}<={L}$12,_xlfn.BINOM.DIST(A{r},{L}$12,$B$5,FALSE),0)").number_format = "0.0000"
        ws[f"{L}11"] = x
        ws[f"{L}12"] = f"=$B$4+{L}11"
        ws[f"{L}13"] = f"=SUMPRODUCT({L}{first}:{L}{last},$B${first}:$B${last})"
        ws[f"{L}14"] = f"=SUMPRODUCT({L}{first}:{L}{last},$C${first}:$C${last})"
        ws[f"{L}15"] = f"={L}13*$B$6"
        ws[f"{L}16"] = f"={L}14*$B$6*$B$7"
        ws[f"{L}17"] = f"={L}15-{L}16"
        ws[f"{L}18"] = f"={L}17-$D$17"
        for r, fmt in [(13, "0.0"), (14, "0.00"), (15, EUR), (16, EUR), (17, EUR), (18, EUR)]:
            ws[f"{L}{r}"].number_format = fmt
        ws.column_dimensions[L].width = 10
    lastL = get_column_letter(4 + MAX_OVERBOOK)
    ws.conditional_formatting.add(f"D17:{lastL}17", ColorScaleRule(start_type="min", start_color="FFFFFF",
                                                                    end_type="max", end_color="60A5FA"))
    ws["E4"], ws["E4"].font = "BEST OVERBOOKING LEVEL (X)", BOLD
    ws["G4"] = f"=INDEX(D11:{lastL}11,MATCH(MAX(D17:{lastL}17),D17:{lastL}17,0))"
    ws["E5"], ws["E5"].font = "Extra net revenue per night vs X=0", BOLD
    ws["G5"] = f"=MAX(D17:{lastL}17)-D17"
    ws["E6"], ws["E6"].font = "Expected guests walked at best X", BOLD
    ws["G6"] = f"=INDEX(D14:{lastL}14,MATCH(MAX(D17:{lastL}17),D17:{lastL}17,0))"
    for c, f in (("G4", "0"), ("G5", EUR), ("G6", "0.00")):
        ws[c].fill, ws[c].font, ws[c].number_format = OUT, BOLD, f
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 18
    ws.freeze_panes = "D12"

    # Python cross-check of the same model (written to the report)
    cap, p, walk = 100, show_prob, 2.0
    best_x, best_net, base = 0, None, None
    for x in range(MAX_OVERBOOK + 1):
        n = cap + x
        k = np.arange(n + 1)
        pk = binom.pmf(k, n, p)
        net = adr * (pk * np.minimum(k, cap)).sum() - adr * walk * (pk * np.maximum(k - cap, 0)).sum()
        base = net if x == 0 else base
        if best_net is None or net > best_net:
            best_x, best_net = x, net
    return {"overbook_best_x": best_x, "overbook_gain_per_night": round(best_net - base, 0),
            "overbook_show_prob": round(p, 3)}


def build_deposit(wb, dec: pd.DataFrame):
    ws = wb.create_sheet("Deposit policy")
    ws["A1"], ws["A1"].font = "Deposit policy on predicted cancellation risk", TITLE
    ws["A2"] = ("Model risk deciles for No-Deposit bookings, Mar-Aug 2017 (unseen by the model). "
                "Policy: ask the riskiest deciles for a deposit of N nights.")
    ws["A2"].font = NOTE
    for i, (lab, val, fmt, note) in enumerate([
            ("Deposit size (nights)", 1, "0", "A cancelled booking forfeits this many nights"),
            ("Guests who walk away when asked for a deposit", 0.05, PCT, "Assumption: they book elsewhere"),
            ("Apply to the riskiest N deciles", 1, "0", "1 = top 10% riskiest bookings")], start=4):
        ws.cell(row=i, column=1, value=lab)
        inp(ws, f"B{i}", val, fmt)
        ws.cell(row=i, column=3, value=note).font = NOTE
    cols = ["Risk decile", "Bookings", "Actual cancel rate", "Cancellations", "Lost revenue",
            "Realized revenue", "First-night value of cancellations", "Applied?",
            "Revenue protected", "Revenue lost to walk-aways", "Net effect"]
    header(ws, 8, cols)
    for i, r in dec.reset_index(drop=True).iterrows():
        row = 9 + i
        vals = [int(r["risk_decile"]), int(r["bookings"]), float(r["actual_cancel_rate"]), int(r["cancellations"]),
                float(r["lost_revenue"]), float(r["realized_revenue"]), float(r["first_night_value_of_cancellations"])]
        for j, v in enumerate(vals, start=1):
            ws.cell(row=row, column=j, value=v).border = THIN
        ws.cell(row=row, column=8, value=f'=IF(A{row}<=$B$6,"Yes","No")')
        ws.cell(row=row, column=9, value=f'=IF(H{row}="Yes",G{row}*$B$4,0)')
        ws.cell(row=row, column=10, value=f'=IF(H{row}="Yes",F{row}*$B$5,0)')
        ws.cell(row=row, column=11, value=f"=I{row}-J{row}")
        ws.cell(row=row, column=3).number_format = PCT
        for c in (5, 6, 7, 9, 10, 11):
            ws.cell(row=row, column=c).number_format = EUR
    tot = 9 + len(dec)
    ws.cell(row=tot, column=1, value="Total").font = BOLD
    for c in (2, 4, 5, 6, 7, 9, 10, 11):
        L = get_column_letter(c)
        cell = ws.cell(row=tot, column=c, value=f"=SUM({L}9:{L}{tot - 1})")
        cell.font, cell.number_format = BOLD, (EUR if c >= 5 else "#,##0")
    ws.cell(row=tot, column=11).fill = OUT
    ws.cell(row=tot + 2, column=1, value="Share of all cancellations covered").font = BOLD
    ws.cell(row=tot + 2, column=2, value=f'=SUMIF(H9:H{tot - 1},"Yes",D9:D{tot - 1})/D{tot}').number_format = PCT
    ws.cell(row=tot + 3, column=1, value="Bookings asked for a deposit").font = BOLD
    ws.cell(row=tot + 3, column=2, value=f'=SUMIF(H9:H{tot - 1},"Yes",B9:B{tot - 1})').number_format = "#,##0"
    ws.column_dimensions["A"].width = 44
    for c in range(2, 12):
        ws.column_dimensions[get_column_letter(c)].width = 16


def build_channel(wb, ch: pd.DataFrame):
    ws = wb.create_sheet("Channel mix")
    ws["A1"], ws["A1"].font = "What if more guests booked direct instead of through online agencies?", TITLE
    ws["A2"] = ("Moves a share of online-travel-agency (OTA) bookings to the direct channel. Shifted bookings take "
                "the direct channel's cancellation behaviour and save the OTA commission.")
    ws["A2"].font = NOTE
    ota, direct = ch.loc["Online travel agency"], ch.loc["Direct"]
    data = [("OTA booked value (all OTA bookings)", float(ota["value"]), EUR, "From data"),
            ("OTA share of value actually earned", float(ota["kept_pct"]) / 100, PCT, "From data"),
            ("Direct share of value actually earned", float(direct["kept_pct"]) / 100, PCT, "From data"),
            ("OTA commission rate", 0.15, PCT, "Assumption: typical 15-20%"),
            ("Share of OTA bookings moved to direct", 0.10, PCT, "Scenario input"),
            ("Cost to acquire a direct booking (% of value)", 0.05, PCT, "Assumption: marketing / loyalty discount")]
    for i, (lab, val, fmt, note) in enumerate(data, start=4):
        ws.cell(row=i, column=1, value=lab)
        if note == "From data":
            ws.cell(row=i, column=2, value=val).number_format = fmt
        else:
            inp(ws, f"B{i}", val, fmt)
        ws.cell(row=i, column=3, value=note).font = NOTE
    out = [("Booked value moved to direct", "=B4*B8", EUR),
           ("Revenue earned on it via OTA (net of commission)", "=B11*B5*(1-B7)", EUR),
           ("Revenue earned on it via direct (net of acquisition cost)", "=B11*B6*(1-B9)", EUR),
           ("NET GAIN from the shift", "=B13-B12", EUR),
           ("Net gain as % of current OTA net revenue", "=B14/(B4*B5*(1-B7))", PCT)]
    for i, (lab, f, fmt) in enumerate(out, start=11):
        ws.cell(row=i, column=1, value=lab).font = BOLD
        c = ws.cell(row=i, column=2, value=f)
        c.number_format, c.fill = fmt, OUT
    ws["A17"] = ("Sensitivity: net gain for different shift shares (rows) and commission rates (columns)")
    ws["A17"].font = BOLD
    shifts = [0.05, 0.10, 0.15, 0.20, 0.25]
    comms = [0.10, 0.15, 0.18, 0.20, 0.25]
    for j, cm in enumerate(comms):
        c = ws.cell(row=18, column=2 + j, value=cm)
        c.number_format, c.font = PCT, BOLD
    for i, sh in enumerate(shifts):
        r = 19 + i
        ws.cell(row=r, column=1, value=sh).number_format = PCT
        for j in range(len(comms)):
            L = get_column_letter(2 + j)
            ws.cell(row=r, column=2 + j,
                    value=f"=$B$4*$A{r}*($B$6*(1-$B$9)-$B$5*(1-{L}$18))").number_format = EUR
    ws.conditional_formatting.add("B19:F23", ColorScaleRule(start_type="min", start_color="FFFFFF",
                                                            end_type="max", end_color="34D399"))
    ws.column_dimensions["A"].width = 52
    for c in "BCDEF":
        ws.column_dimensions[c].width = 16
    v, ok, dk = float(ota["value"]), float(ota["kept_pct"]) / 100, float(direct["kept_pct"]) / 100
    gain = v * 0.10 * (dk * 0.95 - ok * 0.85)
    return {"channel_shift10_gain": round(gain, 0)}


def run() -> dict:
    C.ensure_dirs()
    d = pd.read_csv(C.PROCESSED_DIR / "fact_bookings.csv", parse_dates=["arrival_date", "reservation_status_date"])
    city = d[(d["hotel"] == "City Hotel") & (d["deposit_type"] == "No Deposit") &
             (d["arrival_date"] >= C.MODEL_TEST_START)]
    # Overbooking only has to cover rooms that empty out too late to resell: bookings still on the
    # books 3 days before arrival that then cancel or do not show. Earlier cancellations get resold.
    days_before = (city["arrival_date"] - city["reservation_status_date"]).dt.days
    early_cancel = (city["is_canceled"] == 1) & (city["is_no_show"] == 0) & (days_before > 3)
    on_books = city[~early_cancel]
    show_prob = 1 - on_books["is_canceled"].mean()
    s = d[(d["hotel"] == "City Hotel") & (d["is_canceled"] == 0) & (d["is_paid_stay"] == 1)]
    adr = s["booking_value"].sum() / s["room_nights"].sum()
    dec = pd.read_csv(C.PROCESSED_DIR / "model_deciles.csv")
    ch = pd.read_csv(C.OUTPUT_DIR / "channel_summary.csv", index_col=0)

    wb = Workbook()
    readme = wb.active
    readme.title = "README"
    readme["A1"], readme["A1"].font = "Hotel revenue what-if model", TITLE
    for i, line in enumerate([
            "Yellow cells are inputs. Blue cells are key results. Everything else is a live formula.",
            "Overbooking: the revenue-maximising number of rooms to sell beyond capacity (binomial model).",
            "Deposit policy: revenue protected by asking the riskiest bookings (from the ML model) for a deposit.",
            "Channel mix: value of moving online-agency bookings to the direct channel.",
            "Defaults come from the cleaned data (python/s01-s04); assumptions are labelled in grey.",
            "Simplifications: one night at a time, independent show-ups, no resale of cancelled rooms."], start=3):
        readme[f"A{i}"] = line
    readme.column_dimensions["A"].width = 110
    m = build_overbooking(wb, show_prob, adr)
    build_deposit(wb, dec)
    m.update(build_channel(wb, ch))
    path = C.EXCEL_DIR / "Hotel_Revenue_WhatIf.xlsx"
    wb.save(path)
    print(f"  saved {path.name}")
    return m


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:28s} {v}")
