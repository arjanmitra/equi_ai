"""Score the extraction engine against the corpus's ground truth, per format.

For each file we run extract(), match records to the canonical funds by
(normalized) name, and over a core set of fields measure:

  precision = correct / extracted-non-null   (when it extracts a value, is it right?)
  coverage  = extracted-non-null / possible   (how much of the schema it recovered)

Precision is the headline reliability number; coverage drops legitimately when a
source simply omits a field (e.g. the messy CSV withholds some AUMs). PDF
factsheets use the document path and are only evaluated when an API key is set.

Run:  python scripts/evaluate_corpus.py [corpus_dir]   (default: ./sample_data)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extraction import extract  # noqa: E402
from app.extraction.llm import llm  # noqa: E402
from app.schemas.fund import Fund  # noqa: E402

# Fields compared for accuracy. name is the match key; fund_id/notes excluded
# (id conventions differ per file; notes is free text).
CORE_FIELDS = [
    "strategy", "redemption_frequency", "notice_period_days", "lockup_months",
    "management_fee", "performance_fee", "aum_usd", "inception_date",
]


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def _values_match(field: str, got, want) -> bool:
    if got is None or want is None:
        return got == want
    if field in {"management_fee", "performance_fee", "aum_usd"}:
        return abs(float(got) - float(want)) <= 1e-6 * max(1.0, abs(float(want)))
    if field == "inception_date":
        return _as_date(got) == _as_date(want)
    return str(got) == str(want)


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    return datetime.fromisoformat(str(v)).date()


class Score:
    def __init__(self) -> None:
        self.correct = self.extracted = self.possible = 0
        self.mismatches: list[str] = []
        self.unmatched_records = 0
        self.path = "?"  # extraction path that ran: tabular / document / none

    @property
    def precision(self) -> float:
        return self.correct / self.extracted if self.extracted else 1.0

    @property
    def coverage(self) -> float:
        return self.extracted / self.possible if self.possible else 0.0


def score_file(path: Path, truth_by_name: dict[str, dict]) -> Score:
    result = extract(path.read_bytes(), path.name, Fund)
    score = Score()
    score.path = result.strategy

    for rec in result.records:
        truth = truth_by_name.get(_norm_name(rec.get("name", "")))
        if truth is None:
            score.unmatched_records += 1
            continue
        for field in CORE_FIELDS:
            score.possible += 1
            got = rec.get(field)
            if got is None:
                continue
            score.extracted += 1
            if _values_match(field, got, truth.get(field)):
                score.correct += 1
            else:
                score.mismatches.append(
                    f"{truth['name']}.{field}: got {got!r} want {truth.get(field)!r}"
                )
    return score


def main(corpus_dir: str = "sample_data") -> int:
    base = Path(corpus_dir)
    manifest = json.loads((base / "manifest.json").read_text())
    truth = json.loads((base / "ground_truth.json").read_text())
    truth_by_name = {_norm_name(t["name"]): t for t in truth}

    print(f"{'file':<24}{'path':>10}{'records':>8}{'precision':>11}{'coverage':>10}")
    print("-" * 63)

    # Only deterministic offline formats gate the exit code. Document-path
    # (PDF) scores depend on a live LLM read, so they are reported but never
    # fail the run — flakiness there is expected, not a regression.
    failures = 0
    doc_seen = False
    for entry in manifest:
        if not entry["offline"] and not llm.available:
            print(f"{entry['file']:<24}{'document':>10}{'—':>8}{'(needs API key)':>21}")
            continue

        score = score_file(base / entry["file"], truth_by_name)
        is_doc = score.path == "document"
        doc_seen = doc_seen or is_doc

        bad = score.precision < 1.0 or score.unmatched_records > 0
        if bad and not is_doc:
            failures += 1
        flag = "  <-- check" if (bad and not is_doc) else ""

        print(
            f"{entry['file']:<24}{score.path:>10}{entry['records']:>8}"
            f"{score.precision:>10.0%}{score.coverage:>10.0%}{flag}"
        )
        for m in score.mismatches[:5]:
            print(f"    mismatch: {m}")
        if score.unmatched_records:
            print(f"    unmatched records: {score.unmatched_records}")

    print("-" * 63)
    print("Offline (tabular) formats: 100% precision."
          if failures == 0 else f"{failures} offline file(s) need attention.")
    if doc_seen:
        print("Document-path (PDF) scores shown above — read live via the LLM.")
    elif not llm.available:
        print("Set ANTHROPIC_API_KEY in api/.env to also score the PDF factsheets.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "sample_data"))
