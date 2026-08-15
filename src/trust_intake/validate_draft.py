from __future__ import annotations

from pathlib import Path

from trust_intake.answers import PROSE_MIN, validate_answers
from trust_intake.inventory_lint import lint_inventory
from trust_intake.ledger import build_ledger, unresolved_quantities
from trust_intake.match_inventory import match
from trust_intake.render import is_approved
from trust_intake.run_store import read_json, run_dir, write_json

SHARED_HEADINGS = (
    "## Locked outcome",
    "## Assumptions",
    "## Options",
    "## Devil's advocate",
    "## Recommendation",
)

DOC_HEADINGS = {
    "brd": (
        "## Executive summary",
        "## Problem",
        "## Current product",
        "## Business requirements",
        "## Metrics",
        "## Non-goals",
        "## Ask",
    ),
    "prd": (
        "## Executive summary",
        "## Solution",
        "## Journeys",
        "## Current product",
        "## In scope",
        "## Out of scope",
        "## Acceptance criteria",
        "## Non-goals",
        "## Ask",
    ),
    "business-case": (
        "## Executive summary",
        "## Current product",
        "## Cost",
        "## Impact",
        "## Options comparison",
        "## Non-goals",
        "## Ask",
    ),
    "case-study": ("## Before", "## Intervention", "## After"),
}


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _read_optional(run_id: str, name: str, runs_dir: Path, default: dict) -> dict:
    try:
        return read_json(run_id, name, runs_dir)
    except FileNotFoundError:
        return default


def validate_run(run_id: str, runs_dir: Path, inventory: dict) -> tuple[int, dict]:
    dest = run_dir(run_id, runs_dir)
    dest.mkdir(parents=True, exist_ok=True)
    draft_path = dest / "draft.md"
    memo_path = dest / "workshop-memo.md"
    stage = "draft" if draft_path.is_file() else "memo"
    failures: list[dict] = []

    try:
        answers = read_json(run_id, "answers.json", runs_dir)
    except FileNotFoundError:
        answers = None
        failures.append(_fail("missing_file", "answers.json", "answers.json missing"))

    if answers is not None:
        failures.extend(validate_answers(answers))

    failures.extend(lint_inventory(inventory))

    if not memo_path.is_file():
        failures.append(_fail("missing_memo", "workshop-memo.md", "workshop-memo.md missing"))

    facts = _read_optional(run_id, "facts.json", runs_dir, {"derived": []})
    estimates = _read_optional(run_id, "estimates.json", runs_dir, {"estimates": []})
    overlaps_path = dest / "overlaps.json"
    if overlaps_path.is_file():
        overlaps = read_json(run_id, "overlaps.json", runs_dir)
    elif answers is not None and "title" in answers and "journey" in answers:
        overlaps = match(answers, inventory)
    else:
        overlaps = {"overlaps": []}
        if answers is not None and answers.get("doc_action") == "new":
            failures.append(_fail("missing_file", "overlaps.json", "overlaps.json missing"))

    if answers is not None and answers.get("doc_action") == "new" and overlaps.get("overlaps"):
        override = answers.get("duplicate_override")
        if override is None or len(str(override).strip()) < PROSE_MIN:
            failures.append(
                _fail("duplicate_new", "duplicate_override", "new doc with overlaps needs override >= 40 chars")
            )

    for i, est in enumerate(estimates.get("estimates") or []):
        for field in ("method", "inputs", "range"):
            if not est.get(field):
                failures.append(_fail("incomplete_estimate", f"estimates[{i}].{field}", f"estimate missing {field}"))

    ledger = build_ledger(facts, answers or {}, estimates)
    for path, text in (
        ("workshop-memo.md", memo_path.read_text(encoding="utf-8") if memo_path.is_file() else ""),
        ("draft.md", draft_path.read_text(encoding="utf-8") if draft_path.is_file() else ""),
    ):
        if not text:
            continue
        for token in unresolved_quantities(text, ledger):
            failures.append(_fail("unresolved_quantity", path, f"quantity {token} not on ledger"))

    if stage == "draft":
        if not is_approved(run_id, runs_dir):
            failures.append(_fail("missing_approved", "APPROVED", "draft.md exists without APPROVED"))
        if answers is not None:
            draft_text = draft_path.read_text(encoding="utf-8")
            for heading in (*SHARED_HEADINGS, *DOC_HEADINGS.get(answers.get("doc_type"), ())):
                if heading not in draft_text:
                    failures.append(_fail("missing_heading", heading, f"draft missing {heading}"))

    payload = {"stage": stage, "failures": failures}
    write_json(run_id, "validation.json", payload, runs_dir)
    return (1 if failures else 0, payload)
