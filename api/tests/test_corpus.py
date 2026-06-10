"""Format-agnosticism regression: generate the varied corpus, then prove the
engine recovers the same canonical values from every offline format.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate_corpus import _norm_name, score_file
from scripts.generate_corpus import main as generate


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("corpus")
    generate(str(out))
    return out


@pytest.fixture(scope="module")
def truth_by_name(corpus: Path) -> dict:
    truth = json.loads((corpus / "ground_truth.json").read_text())
    return {_norm_name(t["name"]): t for t in truth}


def _offline_entries(corpus: Path) -> list[dict]:
    manifest = json.loads((corpus / "manifest.json").read_text())
    return [e for e in manifest if e["offline"]]


def test_all_offline_formats_present(corpus: Path):
    kinds = {e["kind"] for e in _offline_entries(corpus)}
    assert {"csv", "xlsx", "html"} <= kinds


@pytest.mark.parametrize(
    "filename",
    ["universe_clean.csv", "universe_messy.csv", "managers.xlsx", "manager_email.html"],
)
def test_format_extracts_at_full_precision(corpus, truth_by_name, filename):
    entry = next(e for e in _offline_entries(corpus) if e["file"] == filename)
    score = score_file(corpus / filename, truth_by_name)

    # Every record maps to a known fund, and every value it extracts is correct.
    assert score.unmatched_records == 0
    assert score.extracted > 0
    assert score.precision == 1.0, score.mismatches


def test_messy_csv_has_lower_coverage_but_still_correct(corpus, truth_by_name):
    # The messy CSV intentionally withholds some values; coverage < 100% while
    # precision stays at 100%. This is the "missing != wrong" guarantee.
    score = score_file(corpus / "universe_messy.csv", truth_by_name)
    assert score.precision == 1.0
    assert score.coverage < 1.0
