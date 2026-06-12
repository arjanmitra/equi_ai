"""Generate a large, adversarial corpus to stress every subsystem.

~120 funds rendered across many messy universe formats (comma/semicolon/tab/pipe
CSVs with synonym headers, bps/%/decimal/bare fees, $B/$M/full AUM, varied date
formats, missing values, junk columns, Latin-1 encoding, multi-sheet XLSX, HTML,
PDFs, and a deliberately adversarial file) — plus thousands of monthly return
rows (long + wide-by-date + a messy file with gaps, dupes, an unmatched fund,
and percent/decimal mixing). Return patterns include wipeouts, zero-vol, short
histories, and deep drawdowns so the metrics/constraint layers get exercised too.

Run:  python scripts/generate_stress_corpus.py [out_dir]   (default sample_data/stress)
Then: python scripts/evaluate_corpus.py sample_data/stress  (extraction accuracy)
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

RNG = random.Random(20240611)
N_FUNDS = 120
END = date(2024, 12, 1)

STRATEGIES = [
    "long_short_equity", "market_neutral", "global_macro", "managed_futures",
    "event_driven", "credit", "relative_value", "multi_strategy",
    "fixed_income", "other",
]
REDEMPTIONS = ["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"]
PATTERNS = ["steady", "volatile", "trending", "flat", "drawdown"]

STRAT_FULL = {
    "long_short_equity": "L/S Equity", "market_neutral": "Market Neutral",
    "global_macro": "Global Macro", "managed_futures": "CTA / Managed Futures",
    "event_driven": "Event Driven", "credit": "Credit",
    "relative_value": "Relative Value", "multi_strategy": "Multi-Strategy",
    "fixed_income": "Fixed Income", "other": "Other",
}
STRAT_ABBR = {
    "long_short_equity": "L/S Equity", "market_neutral": "Market Neutral",
    "global_macro": "Macro", "managed_futures": "CTA",
    "event_driven": "Event-Driven", "credit": "Credit",
    "relative_value": "Relative Value", "multi_strategy": "Multi-Strat",
    "fixed_income": "Fixed Income", "other": "Other",
}

_PREFIX = [
    "Alpha", "Beacon", "Cobalt", "Delta", "Echo", "Fjord", "Granite", "Halcyon",
    "Ironwood", "Juniper", "Kestrel", "Lodestar", "Meridian", "Northgate",
    "Orion", "Pinnacle", "Quartz", "Riverstone", "Summit", "Tideline", "Umbra",
    "Vantage", "Westfield", "Xenon", "Yarrow", "Zephyr", "Ardent", "Brightwater",
    "Cedar", "Drawbridge", "Everest", "Foxhill", "Goldcrest", "Harbour",
]
_SUFFIX = [
    "Capital", "Partners", "Management", "Advisors", "Asset Management", "Fund",
    "Investments", "Global", "Macro Fund", "Credit Opportunities", "Group",
    "Holdings", "Strategies", "Associates",
]
_ACCENTED = ["Zürich Macro Partners", "Crédit Alpha", "São Paulo Capital", "Müller Global"]
_NOTES = [
    "Seasoned team; stable AUM.", "Key-person risk on founder.",
    "Short track record.", "Illiquid underlying positions.",
    "New PM hired 2023.", "AUM withheld pending NDA.", "", "",
    "Concentrated book — top 5 = 60%.", 'Uses "soft" gates in stress.',
]


def _months_ending(end: date, n: int) -> list[date]:
    out, y, m = [], end.year, end.month
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def _gen_returns(n: int, pattern: str) -> list[float]:
    if pattern == "zero":
        return [0.0] * n
    out: list[float] = []
    for i in range(n):
        if pattern == "steady":
            r = RNG.gauss(0.006, 0.015)
        elif pattern == "volatile":
            r = RNG.gauss(0.005, 0.05)
        elif pattern == "trending":
            r = RNG.gauss(0.012, 0.02)
        elif pattern == "flat":
            r = RNG.gauss(0.0, 0.003)
        elif pattern == "drawdown":
            r = RNG.gauss(-0.08, 0.03) if n // 3 <= i < n // 3 + 4 else RNG.gauss(0.008, 0.02)
        else:
            r = RNG.gauss(0.005, 0.02)
        out.append(round(r, 4))
    if pattern == "wipeout" and n > 3:
        out[n // 2] = -0.92
    return out


def _unique_names(n: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < n:
        nm = f"{RNG.choice(_PREFIX)} {RNG.choice(_SUFFIX)}"
        if nm not in seen:
            seen.add(nm)
            names.append(nm)
    return names


def generate_funds() -> list[dict]:
    names = _unique_names(N_FUNDS)
    funds: list[dict] = []
    for i in range(N_FUNDS):
        history = RNG.choice([6, 12, 18, 24, 36, 48, 60, 84, 120])
        pattern = RNG.choice(PATTERNS)
        periods = _months_ending(END, history)
        f = {
            "code": f"F{i + 1:04d}",
            "name": names[i],
            "strategy": RNG.choice(STRATEGIES),
            "redemption": RNG.choice(REDEMPTIONS),
            "notice": RNG.choice([0, 5, 15, 30, 45, 60, 90, 120, 180]),
            "lockup": RNG.choice([0, 0, 6, 12, 12, 24, 36]),
            "mgmt": round(RNG.choice([0.005, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025]), 4),
            "perf": round(RNG.choice([0.0, 0.10, 0.15, 0.175, 0.20, 0.30]), 4),
            "aum": float(RNG.choice([5e6, 25e6, 85e6, 150e6, 450e6, 1.2e9, 3.5e9, 12e9, 20e9])),
            "inception": periods[0],
            "notes": RNG.choice(_NOTES),
            "history": list(zip(periods, _gen_returns(history, pattern))),
        }
        funds.append(f)

    # --- inject deliberate edge cases ---
    funds[0].update(redemption="daily", notice=0, lockup=0)          # ultra-liquid
    funds[1].update(redemption="annual", notice=180, lockup=36)      # ultra-illiquid
    funds[2]["history"] = list(zip(
        _months_ending(END, 24), _gen_returns(24, "wipeout")))        # wipeout month
    funds[3]["history"] = list(zip(
        _months_ending(END, 36), _gen_returns(36, "zero")))           # zero vol
    funds[4]["history"] = list(zip(
        _months_ending(END, 2), _gen_returns(2, "steady")))           # 2 months -> low conf
    funds[5].update(aum=None, mgmt=None, perf=None, notes="")         # missing fields
    funds[6]["name"] = funds[7]["name"]                              # duplicate name
    for k, nm in enumerate(_ACCENTED):
        funds[10 + k]["name"] = nm                                   # accented names
    return funds


# --- value formatters -------------------------------------------------------
def _pct(v):  # 0.02 -> "2%"
    return "" if v is None else f"{v * 100:g}%"

def _bps(v):  # 0.015 -> "150 bps"
    return "" if v is None else f"{round(v * 10000)} bps"

def _dec(v):  # 0.02 -> "0.02"
    return "" if v is None else f"{v:g}"

def _bare_pct(v):  # 0.02 -> "2"  (ambiguous below 1% — a real boundary)
    return "" if v is None else f"{v * 100:g}"

def _aum_full(v):
    return "" if v is None else f"${v:,.0f}"

def _aum_suffix(v):
    if v is None:
        return ""
    return f"${v / 1e9:g}B" if v >= 1e9 else f"${v / 1e6:g}M"

def _aum_m(v):
    return "" if v is None else f"${v / 1e6:g}M"

def _redem_title(r):
    return r.replace("_", "-").title()


def _date(d: date, fmt: str) -> str:
    return d.strftime(fmt)


# --- universe profiles ------------------------------------------------------
def profile_a(f, i):  # clean comma
    return {
        "Fund ID": f["code"], "Fund Name": f["name"],
        "Strategy": STRAT_FULL[f["strategy"]], "Redemption": _redem_title(f["redemption"]),
        "Notice (days)": f["notice"], "Lockup (months)": f["lockup"],
        "Mgmt Fee": _pct(f["mgmt"]), "Perf Fee": _pct(f["perf"]),
        "AUM (USD)": _aum_full(f["aum"]), "Inception": f["inception"].isoformat(),
        "Notes": f["notes"],
    }


_DATE_FORMATS = ["%d %b %Y", "%B %d, %Y", "%m/%d/%Y", "%d-%b-%Y"]


def profile_b(f, i):  # messy semicolon: synonyms, bps, suffix AUM, varied dates, junk, missing
    aum = "" if i % 11 == 0 else _aum_suffix(f["aum"])
    notice = "" if i % 13 == 0 else f"{f['notice']} days"
    return {
        "Manager": f["name"], "Style": STRAT_ABBR[f["strategy"]],
        "Liquidity": f["redemption"].replace("_", " "),
        "Notice": notice, "Lock-Up": f"{f['lockup']} mo",
        "Management": _bps(f["mgmt"]), "Incentive": _pct(f["perf"]),
        "Assets": aum, "Launched": _date(f["inception"], _DATE_FORMATS[i % 4]),
        "Internal Rating": RNG.choice(["A", "B", "C"]),  # junk -> unmapped
        "Commentary": f["notes"],
    }


def profile_c(f, i):  # tab, decimals, $M
    return {
        "Manager Name": f["name"], "Sub-Strategy": f["strategy"],
        "Dealing": _redem_title(f["redemption"]), "Notice Days": f["notice"],
        "Lockup": f["lockup"], "Mgmt": _dec(f["mgmt"]), "Perf": _dec(f["perf"]),
        "Fund Size": _aum_m(f["aum"]), "Inception Date": _date(f["inception"], "%m/%d/%Y"),
        "Comments": f["notes"],
    }


def profile_d(f, i):  # pipe, bare percents, full AUM
    return {
        "Account": f["name"], "Approach": STRAT_FULL[f["strategy"]],
        "Redemption Terms": _redem_title(f["redemption"]), "Notice Period": f["notice"],
        "Lock-up": f["lockup"], "Base Fee": _bare_pct(f["mgmt"]),
        "Carry": _bare_pct(f["perf"]), "AUM": _aum_full(f["aum"]),
        "Vintage": _date(f["inception"], "%B %d, %Y"), "Remarks": f["notes"],
    }


def _write_csv(rows, path, sep=",", encoding="utf-8"):
    pd.DataFrame(rows).to_csv(path, index=False, sep=sep, encoding=encoding)


# --- returns ----------------------------------------------------------------
def write_returns_long(funds, path):
    rows = []
    for k, f in enumerate(funds):
        as_decimal = k % 4 == 0  # mix percent and decimal across funds
        for period, r in f["history"]:
            val = f"{r:g}" if as_decimal else f"{r * 100:g}%"
            rows.append({"Fund": f["name"], "Month": period.isoformat(), "Net Return": val})
    pd.DataFrame(rows).to_csv(path, index=False)
    return len(rows)


def write_returns_wide(funds, path, window=36):
    cols = _months_ending(END, window)
    eligible = [f for f in funds if len(f["history"]) >= window][:30]
    rows = []
    for f in eligible:
        hist = dict(f["history"])
        row = {"Manager": f["name"]}
        for p in cols:
            row[p.strftime("%b-%y")] = f"{hist[p] * 100:g}%" if p in hist else ""
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)
    return len(rows), len(cols)


def write_returns_messy(funds, path):
    rows = []
    for f in funds[:20]:
        for j, (period, r) in enumerate(f["history"]):
            if j % 7 == 3:
                continue  # gaps
            cell = "n/a" if j % 11 == 5 else f"{r * 100:g}%"
            rows.append({"fund": f["name"], "date": period.isoformat(), "return": cell})
    # an unmatched fund + a duplicate (fund, period)
    rows.append({"fund": "Phantom Capital LP", "date": "2024-01-01", "return": "1.1%"})
    if rows:
        rows.append(dict(rows[0]))  # exact duplicate row
    pd.DataFrame(rows).to_csv(path, index=False)
    return len(rows)


def write_adversarial(funds, path):
    """Deliberately hostile: preamble lines, blank rows, duplicate column,
    a combined '2/20' fee column, stray whitespace."""
    lines = [
        "# CONFIDENTIAL — manager universe export",
        "# generated for internal review",
        "Fund Name,Strategy,Fees,Fees,AUM,Notes",
    ]
    for f in funds[:15]:
        fees = f"{(f['mgmt'] or 0) * 100:g}/{(f['perf'] or 0) * 100:g}"
        lines.append(
            f"  {f['name']}  ,{STRAT_FULL[f['strategy']]},{fees},{fees},"
            f"{_aum_suffix(f['aum'])},{f['notes']}"
        )
        if RNG.random() < 0.2:
            lines.append(",,,,,")  # blank row
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_xlsx(funds, path):
    rows = [profile_c(f, i) for i, f in enumerate(funds)]
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        pd.DataFrame(rows).to_excel(xl, sheet_name="Funds", index=False)
        pd.DataFrame({"Disclaimer": ["Indicative terms. Internal use only."]}).to_excel(
            xl, sheet_name="Disclaimer", index=False)


def write_html(funds, path):
    body = "\n".join(
        f"<tr><td>{f['name']}</td><td>{STRAT_FULL[f['strategy']]}</td>"
        f"<td>{_redem_title(f['redemption'])}</td><td>{_pct(f['mgmt'])}</td>"
        f"<td>{_pct(f['perf'])}</td><td>{_aum_suffix(f['aum'])}</td>"
        f"<td>{f['inception'].strftime('%B %d, %Y')}</td></tr>"
        for f in funds
    )
    html = f"""<!DOCTYPE html><html><body>
<div><b>From:</b> placement@example-im.com</div>
<div><b>Subject:</b> Manager universe</div>
<table border="1"><thead><tr>
<th>Fund Name</th><th>Strategy</th><th>Liquidity</th><th>Mgmt Fee</th>
<th>Perf Fee</th><th>AUM</th><th>Inception</th></tr></thead>
<tbody>{body}</tbody></table></body></html>"""
    Path(path).write_text(html, encoding="utf-8")


def write_pdf(f, path):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    def line(pdf, h, txt, style="", size=11):
        pdf.set_font("Helvetica", style, size)
        safe = txt.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, h, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    aum = f"${f['aum'] / 1e9:g} billion" if f["aum"] and f["aum"] >= 1e9 else f"${(f['aum'] or 0) / 1e6:g} million"
    pdf = FPDF()
    pdf.add_page()
    line(pdf, 10, f["name"], "B", 16)
    line(pdf, 6, f"{f['name']} is a {STRAT_FULL[f['strategy']].lower()} fund launched "
                 f"on {f['inception'].strftime('%B %d, %Y')}, managing approximately {aum}. "
                 f"It offers {f['redemption']} liquidity with {f['notice']} days' notice "
                 f"and a {f['lockup']}-month lockup.")
    line(pdf, 8, "Key Terms", "B", 12)
    for label, val in [
        ("Strategy", STRAT_FULL[f["strategy"]]), ("AUM", _aum_suffix(f["aum"])),
        ("Management Fee", _pct(f["mgmt"])), ("Performance Fee", _pct(f["perf"])),
        ("Redemption", _redem_title(f["redemption"])),
        ("Notice", f"{f['notice']} days"), ("Lockup", f"{f['lockup']} months"),
    ]:
        line(pdf, 6, f"{label}: {val}")
    pdf.output(str(path))


def _canonical(f):
    return {
        "name": f["name"], "strategy": f["strategy"],
        "redemption_frequency": f["redemption"], "notice_period_days": f["notice"],
        "lockup_months": f["lockup"], "management_fee": f["mgmt"],
        "performance_fee": f["perf"],
        "aum_usd": None if f["aum"] is None else float(f["aum"]),
        "inception_date": f["inception"].isoformat(), "notes": f["notes"],
    }


def main(out_dir="sample_data/stress"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    funds = generate_funds()
    names = lambda fs: [f["name"] for f in fs]  # noqa: E731

    _write_csv([profile_a(f, i) for i, f in enumerate(funds)], out / "universe_a.csv")
    _write_csv([profile_b(f, i) for i, f in enumerate(funds)], out / "universe_b.csv", sep=";")
    _write_csv([profile_c(f, i) for i, f in enumerate(funds[:60])], out / "universe_c.tsv", sep="\t")
    _write_csv([profile_d(f, i) for i, f in enumerate(funds[60:])], out / "universe_pipe.csv", sep="|")
    accented = funds[10:14] + funds[20:30]
    # Windows-1252 (the usual Excel "save as CSV" encoding) — accented names +
    # em dashes/curly quotes; tests non-UTF-8 detection.
    _write_csv([profile_a(f, i) for i, f in enumerate(accented)], out / "universe_win1252.csv", encoding="cp1252")
    write_xlsx(funds[:40], out / "managers.xlsx")
    write_html(funds[:15], out / "manager_email.html")
    write_adversarial(funds, out / "universe_adversarial.csv")
    for f in funds[:3]:
        write_pdf(f, out / f"factsheet_{f['code']}.pdf")

    n_long = write_returns_long(funds, out / "returns_long.csv")
    n_wide, n_cols = write_returns_wide(funds, out / "returns_wide.csv")
    n_messy = write_returns_messy(funds, out / "returns_messy.csv")

    (out / "ground_truth.json").write_text(json.dumps([_canonical(f) for f in funds], indent=2))

    manifest = [
        {"file": "universe_a.csv", "kind": "csv", "offline": True, "records": len(funds), "funds": names(funds)},
        {"file": "universe_b.csv", "kind": "csv", "offline": True, "records": len(funds), "funds": names(funds)},
        {"file": "universe_c.tsv", "kind": "tsv", "offline": True, "records": 60, "funds": names(funds[:60])},
        {"file": "universe_pipe.csv", "kind": "csv", "offline": True, "records": 60, "funds": names(funds[60:])},
        {"file": "universe_win1252.csv", "kind": "csv", "offline": True, "records": len(accented), "funds": names(accented)},
        {"file": "managers.xlsx", "kind": "xlsx", "offline": True, "records": 40, "funds": names(funds[:40])},
        {"file": "manager_email.html", "kind": "html", "offline": True, "records": 15, "funds": names(funds[:15])},
        {"file": "universe_adversarial.csv", "kind": "csv", "offline": True, "records": 15, "funds": names(funds[:15])},
        {"file": "factsheet_F0001.pdf", "kind": "pdf", "offline": False, "records": 1, "funds": [funds[0]["name"]]},
    ]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"Wrote {N_FUNDS} funds to {out}/")
    print(f"  universe files: a/b/c/pipe/latin1 CSV + xlsx + html + adversarial + 3 PDFs")
    print(f"  returns: long={n_long} rows, wide={n_wide}x{n_cols}, messy={n_messy} rows")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_data/stress")
