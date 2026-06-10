"""Generate the IC memo with the LLM, under the grounding verifier.

The model sees only the catalog (a list of facts with stable IDs) and must cite
the IDs each claim rests on. We verify every draft; if any claim's numbers
aren't grounded in its cited facts, we re-prompt with the specific problems and
regenerate (capped). Survivors after the cap are returned flagged, not dropped.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.config import settings
from app.extraction.llm import llm
from app.memo.verify import verify_memo
from app.schemas.catalog import Catalog
from app.schemas.memo import MemoDraft, VerifiedMemo

_SYSTEM = """You are an investment analyst drafting a concise investment-committee
(IC) memo for an allocator, based ONLY on a provided catalog of computed facts.

Absolute rules:
1. State only facts present in the FACTS catalog. Never invent, infer, or
   recompute a number.
2. Every claim must list the exact fact ID(s) it relies on in `refs`. Any claim
   that states a number MUST cite the fact that number comes from.
3. Use values as shown (you may round sensibly). Never write a number that does
   not appear in a fact you cite.
4. Be concise and decision-useful — a ~1 page memo, one sentence per claim.

Produce three sections:
- summary: the mandate being evaluated and the headline recommendation.
- recommendation: the ranked shortlist — which funds pass and why they rank
  where they do, citing their metrics and constraint checks; briefly note
  notable exclusions.
- risks: key risks and caveats — low-confidence metrics (short track records),
  weak benchmark proxies, binding constraints — citing the facts.

Cite generously: prefer specific metric/check facts over vague statements."""


def render_catalog(catalog: Catalog) -> str:
    lines = ["MANDATE CONSTRAINTS:"]
    if not catalog.mandate:
        lines.append("  (none specified)")
    for f in catalog.mandate:
        lines.append(f"  {f.id} | {f.label} = {f.display}")

    lines.append("\nFUNDS (ranked):")
    for ff in catalog.funds:
        status = "SHORTLISTED" if ff.passed else "EXCLUDED"
        lines.append(f"\n[{ff.rank}] {ff.fund_name} — {status}, score {ff.score:.0f}")
        for group, facts in (
            ("fields", ff.fields),
            ("metrics", ff.metrics),
            ("checks", ff.checks),
        ):
            if not facts:
                continue
            lines.append(f"  {group}:")
            for f in facts:
                if f.kind == "check":
                    lines.append(f"    {f.id} | {f.label}: {f.value} — {f.display}")
                else:
                    lines.append(f"    {f.id} | {f.label} = {f.display}")
    return "\n".join(lines)


def _user(rendered: str, feedback: str | None = None) -> str:
    base = (
        f"FACTS:\n{rendered}\n\n"
        "Write the IC memo now. Cite fact IDs in `refs` for every claim."
    )
    if feedback:
        base += (
            "\n\nYour previous draft contained claims whose numbers are NOT "
            f"grounded in their cited facts:\n{feedback}\n"
            "Rewrite the memo so EVERY number matches a cited fact, or remove the "
            "unsupported figure. Cite the correct fact IDs."
        )
    return base


def generate_memo(
    catalog: Catalog, max_attempts: int | None = None
) -> tuple[VerifiedMemo, list[str]]:
    cap = max_attempts if max_attempts is not None else settings.max_repair_attempts
    rendered = render_catalog(catalog)
    user = _user(rendered)
    log: list[str] = []
    last: VerifiedMemo | None = None

    for attempt in range(cap + 1):
        raw = llm.structured(
            model=settings.memo_model,
            system=_SYSTEM,
            user_text=user,
            schema=MemoDraft,
            max_tokens=4096,
        )
        try:
            draft = MemoDraft.model_validate(raw)
        except ValidationError as exc:
            log.append(f"attempt {attempt + 1}: invalid structure ({exc.error_count()} errors)")
            user = _user(rendered) + "\n\nReturn the memo strictly in the required schema."
            continue

        verified = verify_memo(draft, catalog)
        last = verified
        n_claims = sum(len(s.claims) for s in verified.sections)
        if verified.all_verified:
            log.append(f"attempt {attempt + 1}: all {n_claims} claims grounded")
            return verified, log

        problems = "\n".join(
            f'- "{c.text}": {"; ".join(c.issues)}' for c in verified.unverified
        )
        log.append(f"attempt {attempt + 1}: {len(verified.unverified)} ungrounded claim(s)")
        user = _user(rendered, feedback=problems)

    log.append("max attempts reached; remaining ungrounded claims flagged")
    return last or VerifiedMemo(sections=[]), log
