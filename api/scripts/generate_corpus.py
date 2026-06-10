"""Generate a deliberately-varied test corpus from one set of ground-truth funds.

The point is to PROVE the extraction engine is format-agnostic: the same funds
are emitted in five inconsistent shapes — different column names, orders,
delimiters, fee conventions (%, bps, bare decimal), AUM conventions ($1.2B vs
$1200M vs full integer), date formats, missing values, junk columns, and file
types (CSV, XLSX, HTML email, PDF factsheet). A correct engine recovers the same
canonical values from all of them.

Run:  python scripts/generate_corpus.py [out_dir]   (default: ./sample_data)

Outputs each file plus `ground_truth.json` (the canonical values) and
`manifest.json` (which files exist, record counts, and which are offline-eval'able).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Allow running as a plain script from the api/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

# --- Canonical ground truth -------------------------------------------------
# Fees are decimals; aum is absolute USD; dates are real (full) dates so every
# format can preserve the day and round-trip exactly.
FUNDS: list[dict] = [
    dict(name="Alpha Macro Partners", strategy="global_macro", redemption="monthly",
         notice=30, lockup=12, mgmt=0.02, perf=0.20, aum=1_200_000_000,
         inception=date(2018, 1, 15), notes="Seasoned macro team; stable AUM."),
    dict(name="Beacon Long/Short Equity", strategy="long_short_equity", redemption="quarterly",
         notice=60, lockup=24, mgmt=0.015, perf=0.15, aum=450_000_000,
         inception=date(2015, 6, 1), notes="Key-person risk on founder."),
    dict(name="Cobalt Managed Futures", strategy="managed_futures", redemption="monthly",
         notice=30, lockup=0, mgmt=0.01, perf=0.20, aum=85_000_000,
         inception=date(2020, 3, 10), notes="Short track record; new strategy."),
    dict(name="Delta Credit", strategy="credit", redemption="quarterly",
         notice=90, lockup=12, mgmt=0.0175, perf=0.175, aum=2_100_000_000,
         inception=date(2012, 9, 1), notes="Illiquid underlying positions."),
    dict(name="Echo Multi-Strat", strategy="multi_strategy", redemption="monthly",
         notice=45, lockup=6, mgmt=0.02, perf=0.20, aum=760_000_000,
         inception=date(2019, 11, 1), notes="Diversified, multi-PM book."),
    dict(name="Fjord Market Neutral", strategy="market_neutral", redemption="monthly",
         notice=15, lockup=0, mgmt=0.0125, perf=0.15, aum=320_000_000,
         inception=date(2017, 4, 1), notes="Low net exposure."),
    dict(name="Granite Event Driven", strategy="event_driven", redemption="quarterly",
         notice=60, lockup=12, mgmt=0.015, perf=0.20, aum=540_000_000,
         inception=date(2014, 2, 1), notes="Merger-arb concentration."),
]

# Strategy wording per format (all must map to the same canonical enum value).
STRAT_FULL = {
    "global_macro": "Global Macro", "long_short_equity": "L/S Equity",
    "managed_futures": "CTA / Managed Futures", "credit": "Credit",
    "multi_strategy": "Multi-Strategy", "market_neutral": "Market Neutral",
    "event_driven": "Event Driven",
}
STRAT_ABBR = {
    "global_macro": "Macro", "long_short_equity": "L/S Equity",
    "managed_futures": "CTA", "credit": "Credit",
    "multi_strategy": "Multi-Strat", "market_neutral": "Market Neutral",
    "event_driven": "Event-Driven",
}


def _aum_suffix(aum: float) -> str:
    return f"${aum / 1e9:g}B" if aum >= 1e9 else f"${aum / 1e6:g}M"


def _redemption_label(value: str) -> str:
    return value.replace("_", "-").title()


# --- Format A: clean comma CSV, %, full-integer AUM, ISO dates --------------
def write_csv_clean(funds: list[dict], path: Path) -> None:
    rows = []
    for i, f in enumerate(funds):
        rows.append({
            "Fund ID": f"F{i + 1:03d}",
            "Fund Name": f["name"],
            "Strategy": STRAT_FULL[f["strategy"]],
            "Redemption": _redemption_label(f["redemption"]),
            "Notice (days)": f["notice"],
            "Lockup (months)": f["lockup"],
            "Mgmt Fee": f"{f['mgmt'] * 100:g}%",
            "Perf Fee": f"{f['perf'] * 100:g}%",
            "AUM (USD)": f"${f['aum']:,.0f}",
            "Inception": f["inception"].isoformat(),
            "Notes": f["notes"],
        })
    pd.DataFrame(rows).to_csv(path, index=False)


# --- Format B: messy ';' CSV, synonym/reordered headers, bps fees, suffix AUM,
#     varied dates, missing values, a junk column, no id column ---------------
def write_csv_messy(funds: list[dict], path: Path) -> None:
    rows = []
    for i, f in enumerate(funds):
        # Deliberate gaps: Echo withholds AUM, Granite withholds notice.
        aum = "" if f["name"].startswith("Echo") else _aum_suffix(f["aum"])
        notice = "" if f["name"].startswith("Granite") else f"{f['notice']} days"
        rows.append({
            "Manager": f["name"],
            "Style": STRAT_ABBR[f["strategy"]],
            "Liquidity": f["redemption"],
            "Notice": notice,
            "Lock-Up": f"{f['lockup']} mo",
            "Management": f"{round(f['mgmt'] * 10000)} bps",
            "Incentive": f"{f['perf'] * 100:g}%",
            "Assets": aum,
            "Launched": f["inception"].strftime("%d %b %Y"),
            "Internal Rating": "A" if i % 2 == 0 else "B",  # junk -> unmapped
            "Commentary": f["notes"],
        })
    pd.DataFrame(rows).to_csv(path, index=False, sep=";")


# --- Format C: multi-sheet XLSX, more synonyms, bare-decimal fees, $M AUM ----
def write_xlsx(funds: list[dict], path: Path) -> None:
    rows = []
    for f in funds:
        rows.append({
            "Manager Name": f["name"],
            "Sub-Strategy": f["strategy"],  # canonical enum value form
            "Dealing": _redemption_label(f["redemption"]),
            "Notice Days": f["notice"],
            "Lockup": f["lockup"],
            "Mgmt": f["mgmt"],   # bare decimal 0.02
            "Perf": f["perf"],
            "Fund Size": f"${f['aum'] / 1e6:g}M",
            "Inception Date": f["inception"].strftime("%m/%d/%Y"),
            "Comments": f["notes"],
        })
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        pd.DataFrame(rows).to_excel(xl, sheet_name="Funds", index=False)
        pd.DataFrame({"Disclaimer": ["For internal use only. Indicative terms."]}).to_excel(
            xl, sheet_name="Disclaimer", index=False
        )


# --- Format D: HTML email with an embedded table (subset of fields) ----------
def write_html(funds: list[dict], path: Path) -> None:
    body_rows = "\n".join(
        f"<tr><td>{f['name']}</td><td>{STRAT_FULL[f['strategy']]}</td>"
        f"<td>{_redemption_label(f['redemption'])}</td>"
        f"<td>{f['mgmt'] * 100:g}%</td><td>{f['perf'] * 100:g}%</td>"
        f"<td>{_aum_suffix(f['aum'])}</td>"
        f"<td>{f['inception'].strftime('%B %d, %Y')}</td></tr>"
        for f in funds
    )
    html = f"""<!DOCTYPE html><html><body>
<div><b>From:</b> placement@example-im.com</div>
<div><b>To:</b> allocator@fund.com</div>
<div><b>Subject:</b> Manager universe — indicative terms</div>
<p>Hi — please find the current shortlist below. Reach out with questions.</p>
<table border="1">
  <thead><tr>
    <th>Fund Name</th><th>Strategy</th><th>Liquidity</th>
    <th>Mgmt Fee</th><th>Perf Fee</th><th>AUM</th><th>Inception</th>
  </tr></thead>
  <tbody>
{body_rows}
  </tbody>
</table>
<p>Best,<br/>Placement Team</p>
</body></html>"""
    path.write_text(html, encoding="utf-8")


# --- Format E: native-text PDF factsheet (single fund; document path) --------
def write_pdf_factsheet(f: dict, path: Path) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    def line(pdf: "FPDF", h: float, text: str) -> None:
        # Reset to the left margin after each block so w=0 cells keep full width.
        pdf.multi_cell(0, h, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    aum_words = (
        f"${f['aum'] / 1e9:g} billion" if f["aum"] >= 1e9 else f"${f['aum'] / 1e6:g} million"
    )
    prose = (
        f"{f['name']} is a {STRAT_FULL[f['strategy']].lower()} hedge fund launched on "
        f"{f['inception'].strftime('%B %d, %Y')}. The fund manages approximately "
        f"{aum_words} in assets. It offers {f['redemption']} liquidity with "
        f"{f['notice']} days' notice and a {f['lockup']}-month initial lockup. "
        f"Management notes: {f['notes']}"
    )
    terms = [
        ("Fund Name", f["name"]),
        ("Strategy", STRAT_FULL[f["strategy"]]),
        ("Inception", f["inception"].strftime("%B %d, %Y")),
        ("AUM", _aum_suffix(f["aum"])),
        ("Redemption Frequency", _redemption_label(f["redemption"])),
        ("Notice Period", f"{f['notice']} days"),
        ("Lock-up", f"{f['lockup']} months"),
        ("Management Fee", f"{f['mgmt'] * 100:g}%"),
        ("Performance Fee", f"{f['perf'] * 100:g}%"),
    ]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    line(pdf, 10, f["name"])
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    line(pdf, 6, prose)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    line(pdf, 8, "Key Terms")
    pdf.set_font("Helvetica", "", 11)
    for label, value in terms:
        line(pdf, 6, f"{label}: {value}")
    pdf.output(str(path))


def _canonical(f: dict) -> dict:
    return {
        "name": f["name"], "strategy": f["strategy"],
        "redemption_frequency": f["redemption"], "notice_period_days": f["notice"],
        "lockup_months": f["lockup"], "management_fee": f["mgmt"],
        "performance_fee": f["perf"], "aum_usd": float(f["aum"]),
        "inception_date": f["inception"].isoformat(), "notes": f["notes"],
    }


def main(out_dir: str = "sample_data") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    write_csv_clean(FUNDS, out / "universe_clean.csv")
    write_csv_messy(FUNDS, out / "universe_messy.csv")
    write_xlsx(FUNDS[:4], out / "managers.xlsx")
    write_html(FUNDS[:3], out / "manager_email.html")
    write_pdf_factsheet(FUNDS[0], out / "factsheet_alpha.pdf")
    write_pdf_factsheet(FUNDS[1], out / "factsheet_beacon.pdf")

    (out / "ground_truth.json").write_text(
        json.dumps([_canonical(f) for f in FUNDS], indent=2)
    )

    manifest = [
        {"file": "universe_clean.csv", "kind": "csv", "offline": True,
         "records": len(FUNDS), "funds": [f["name"] for f in FUNDS]},
        {"file": "universe_messy.csv", "kind": "csv", "offline": True,
         "records": len(FUNDS), "funds": [f["name"] for f in FUNDS]},
        {"file": "managers.xlsx", "kind": "xlsx", "offline": True,
         "records": 4, "funds": [f["name"] for f in FUNDS[:4]]},
        {"file": "manager_email.html", "kind": "html", "offline": True,
         "records": 3, "funds": [f["name"] for f in FUNDS[:3]]},
        {"file": "factsheet_alpha.pdf", "kind": "pdf", "offline": False,
         "records": 1, "funds": [FUNDS[0]["name"]]},
        {"file": "factsheet_beacon.pdf", "kind": "pdf", "offline": False,
         "records": 1, "funds": [FUNDS[1]["name"]]},
    ]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"Wrote {len(manifest)} files + ground_truth.json + manifest.json to {out}/")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_data")
