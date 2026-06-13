"""Structure recovery: finding the real table inside an adversarial grid.

These exercise `recover_grid` directly (unit) and end-to-end through `extract`
on a deliberately hostile CSV (preamble comments, blank rows, ragged rows,
duplicate columns). The contract under test is *graceful degradation*: a messy
file still yields records and never collapses to strategy="none".
"""

from __future__ import annotations

from pathlib import Path

from app.extraction import extract
from app.extraction.structure import recover_grid
from app.schemas.fund import Fund

FIXTURES = Path(__file__).parent / "fixtures"


# --- unit: recover_grid ----------------------------------------------------

def test_clean_grid_is_untouched():
    grid = [["Name", "Fee"], ["Alpha", "2%"], ["Beacon", "1.5%"]]
    df, notes = recover_grid(grid)
    assert list(df.columns) == ["Name", "Fee"]
    assert df.shape == (2, 2)
    assert notes == []  # a clean grid produces no edits


def test_preamble_rows_are_skipped():
    grid = [
        ["# confidential export"],
        ["# generated for review"],
        ["Name", "Strategy", "AUM"],
        ["Alpha", "Macro", "$1.2B"],
    ]
    df, notes = recover_grid(grid)
    assert list(df.columns) == ["Name", "Strategy", "AUM"]
    assert df.shape == (1, 3)
    assert any("skipped 2 preamble" in n for n in notes)


def test_blank_rows_dropped():
    grid = [["Name", "Fee"], [], ["Alpha", "2%"], ["", ""], ["Beacon", "1%"]]
    df, notes = recover_grid(grid)
    assert df.shape == (2, 2)
    assert any("blank row" in n for n in notes)


def test_duplicate_columns_deduped():
    grid = [["Name", "Fees", "Fees"], ["Alpha", "2", "20"]]
    df, notes = recover_grid(grid)
    assert list(df.columns) == ["Name", "Fees", "Fees.1"]
    assert any("de-duplicated" in n for n in notes)


def test_ragged_rows_reconciled_to_modal_width():
    grid = [
        ["Name", "Strategy", "AUM"],
        ["Alpha", "Macro", "$1B", "EXTRA", "TRAILING"],  # too long
        ["Beacon", "Credit"],  # too short
    ]
    df, notes = recover_grid(grid)
    assert df.shape == (2, 3)
    assert df.iloc[1]["AUM"] == ""  # short row padded, not crashed
    assert any("ragged" in n for n in notes)


def test_empty_grid_degrades_gracefully():
    df, notes = recover_grid([])
    assert df.empty
    assert notes  # explains why


# --- end-to-end through extract -------------------------------------------

def test_adversarial_file_recovers_not_none():
    raw = (FIXTURES / "adversarial_universe.csv").read_bytes()
    result = extract(raw, "adversarial_universe.csv", Fund)

    # The headline guarantee: a hostile file still goes down the tabular path
    # and yields records, rather than collapsing to strategy="none".
    assert result.strategy == "tabular"
    assert result.report.records_ok == 3
    names = {r["name"] for r in result.records}
    assert {"Alpha Macro Partners", "Beacon L/S Equity", "Cobalt Managed Futures"} <= names


def test_adversarial_structure_notes_surfaced():
    raw = (FIXTURES / "adversarial_universe.csv").read_bytes()
    result = extract(raw, "adversarial_universe.csv", Fund)
    notes = [i.message for i in result.report.issues if i.message.startswith("structure:")]
    joined = " ".join(notes)
    assert "preamble" in joined
    assert "de-duplicated" in joined
    assert "ragged" in joined


# --- attribute bag (extra/unmapped columns) --------------------------------
# These run under the offline heuristic (conftest forces it), which deterministically
# leaves schema-foreign stat columns unmapped — exactly the case the bag handles.

def test_extra_columns_captured_as_attributes():
    raw = (FIXTURES / "extra_columns_universe.csv").read_bytes()
    result = extract(raw, "extra_columns_universe.csv", Fund)
    extras = [p for p in result.provenance if p.kind == "extra"]
    captured = {p.target_field for p in extras}
    assert {"Sortino Ratio", "ESG Score", "PM Tenure"} <= captured


def test_extras_attributed_to_their_source_column():
    raw = (FIXTURES / "extra_columns_universe.csv").read_bytes()
    result = extract(raw, "extra_columns_universe.csv", Fund)
    sortino = next(
        p for p in result.provenance
        if p.kind == "extra" and p.target_field == "Sortino Ratio"
        and result.records[p.record_index]["name"] == "Alpha Macro Partners"
    )
    assert sortino.source == "column: Sortino Ratio"
    assert sortino.normalized_value == "1.42"  # verbatim, no coercion
    assert sortino.transform is None


def test_extras_never_leak_into_records():
    """The trust wall: an attribute must never become a canonical Fund field."""
    raw = (FIXTURES / "extra_columns_universe.csv").read_bytes()
    result = extract(raw, "extra_columns_universe.csv", Fund)
    fund_fields = set(Fund.model_fields)
    for rec in result.records:
        assert set(rec).issubset(fund_fields)
        assert "Sortino Ratio" not in rec
        assert "ESG Score" not in rec
