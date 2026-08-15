from pathlib import Path

import pytest

from trust_intake.ledger import build_ledger
from trust_intake.render import (
    is_approved,
    render_doc,
    render_memo,
    render_to_run,
    write_approved,
)
from trust_intake.run_store import init_run, write_json

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

EXTRA_HEADINGS = {
    "brd": ["## Problem", "## Business requirements", "## Metrics", "## Non-goals"],
    "prd": ["## Solution", "## Journeys", "## In scope", "## Out of scope", "## Acceptance criteria", "## Non-goals"],
    "business-case": ["## Cost", "## Impact", "## Options comparison", "## Ask"],
    "case-study": ["## Before", "## Intervention", "## After"],
}


def _bundle(answers: dict) -> tuple[dict, dict, dict, list[dict]]:
    facts = {"derived": [{"name": "euro_impact", "value": 2_500_000, "unit": "EUR"}]}
    overlaps = {"overlaps": []}
    estimates = {
        "estimates": [
            {
                "name": "rate",
                "value": 0.12,
                "unit": "%",
                "source": "ESTIMATE",
                "method": "run-rate",
                "inputs": ["partial_rate"],
                "range": {"low": 0.096, "high": 0.144},
            }
        ]
    }
    ledger = build_ledger(facts, answers, estimates)
    return facts, overlaps, estimates, ledger


def test_each_doc_has_extra_headings_advocate_do_nothing_and_ledger_volume(complete_answers):
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    for doc_type, headings in EXTRA_HEADINGS.items():
        text = render_doc(doc_type, complete_answers, facts, overlaps, estimates, ledger, TEMPLATES)
        for heading in headings:
            assert heading in text, f"{doc_type} missing {heading}"
        assert "Devil's advocate" in text
        assert "do-nothing" in text
        assert "{{ledger.volume}}" not in text
        assert "10000" in text


def test_render_memo_has_advocate_do_nothing_and_ledger_volume(complete_answers):
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    text = render_memo(complete_answers, facts, overlaps, estimates, ledger, TEMPLATES)
    assert "Devil's advocate" in text
    assert "do-nothing" in text
    assert "{{ledger.volume}}" not in text
    assert "10000" in text


def test_ledger_formats_eur_and_percent(complete_answers):
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    text = render_doc("business-case", complete_answers, facts, overlaps, estimates, ledger, TEMPLATES)
    assert "€2.5M" in text
    assert "12.00%" in text


def test_empty_required_prose_raises(complete_answers):
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    complete_answers["devils_advocate"]["why_fails"] = ""
    with pytest.raises(ValueError):
        render_memo(complete_answers, facts, overlaps, estimates, ledger, TEMPLATES)


def test_render_to_run_without_approved_raises(tmp_path: Path, complete_answers):
    dest = init_run("Holdout for refunds", runs_dir=tmp_path)
    with pytest.raises(PermissionError):
        render_to_run(dest.name, tmp_path, TEMPLATES)


def test_write_approved_then_render_to_run(tmp_path: Path, complete_answers):
    dest = init_run("Holdout for refunds", runs_dir=tmp_path)
    run_id = dest.name
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    write_json(run_id, "answers.json", complete_answers, tmp_path)
    write_json(run_id, "facts.json", facts, tmp_path)
    write_json(run_id, "overlaps.json", overlaps, tmp_path)
    write_json(run_id, "estimates.json", estimates, tmp_path)
    path = write_approved(run_id, tmp_path)
    assert path.name == "APPROVED"
    assert path.read_text(encoding="utf-8") == ""
    assert is_approved(run_id, tmp_path)
    draft = render_to_run(run_id, tmp_path, TEMPLATES)
    assert draft.name == "draft.md"
    text = draft.read_text(encoding="utf-8")
    assert "Devil's advocate" in text
    assert "do-nothing" in text
    assert "{{ledger.volume}}" not in text
    assert "10000" in text


def test_render_memo_writes_without_approved(tmp_path: Path, complete_answers):
    dest = init_run("Holdout for refunds", runs_dir=tmp_path)
    facts, overlaps, estimates, ledger = _bundle(complete_answers)
    text = render_memo(
        complete_answers, facts, overlaps, estimates, ledger, TEMPLATES, run_id=dest.name, runs_dir=tmp_path
    )
    memo = dest / "workshop-memo.md"
    assert memo.is_file()
    assert memo.read_text(encoding="utf-8") == text
    assert not is_approved(dest.name, tmp_path)
