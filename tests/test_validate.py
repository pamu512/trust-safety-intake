from pathlib import Path

from trust_intake.ledger import build_ledger
from trust_intake.render import render_memo, render_to_run, write_approved
from trust_intake.run_store import init_run, write_json
from trust_intake.validate_draft import validate_run

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

CLEAN_INVENTORY = {
    "brands": ["foodora", "foodpanda", "yemeksepeti"],
    "journeys": ["account", "promo", "checkout", "claims-cancel", "payout", "cross-journey"],
    "stack": [{"id": "rules", "name": "Rules engine", "layer": "decisioning", "notes": ""}],
    "controls": [],
    "docs": [],
}


def _bundle(answers: dict) -> tuple[dict, dict, dict, list[dict]]:
    facts = {"derived": []}
    overlaps = {"overlaps": []}
    estimates = {"estimates": []}
    return facts, overlaps, estimates, build_ledger(facts, answers, estimates)


def _write_memo_run(tmp_path: Path, answers: dict) -> str:
    dest = init_run("Holdout for refunds", runs_dir=tmp_path)
    run_id = dest.name
    facts, overlaps, estimates, ledger = _bundle(answers)
    write_json(run_id, "answers.json", answers, tmp_path)
    write_json(run_id, "facts.json", facts, tmp_path)
    write_json(run_id, "overlaps.json", overlaps, tmp_path)
    write_json(run_id, "estimates.json", estimates, tmp_path)
    render_memo(answers, facts, overlaps, estimates, ledger, TEMPLATES, run_id=run_id, runs_dir=tmp_path)
    return run_id


def test_golden_complete_run_exits_0_draft_stage(tmp_path: Path, complete_answers):
    run_id = _write_memo_run(tmp_path, complete_answers)
    write_approved(run_id, tmp_path)
    render_to_run(run_id, tmp_path, TEMPLATES)
    code, result = validate_run(run_id, tmp_path, CLEAN_INVENTORY)
    assert code == 0
    assert result["stage"] == "draft"
    assert result["failures"] == []
    written = (tmp_path / run_id / "validation.json").read_text(encoding="utf-8")
    assert '"stage": "draft"' in written


def test_missing_devils_advocate_exits_1(tmp_path: Path, complete_answers):
    complete_answers["devils_advocate"]["why_fails"] = ""
    dest = init_run("Holdout for refunds", runs_dir=tmp_path)
    run_id = dest.name
    facts, overlaps, estimates, _ledger = _bundle(complete_answers)
    write_json(run_id, "answers.json", complete_answers, tmp_path)
    write_json(run_id, "facts.json", facts, tmp_path)
    write_json(run_id, "overlaps.json", overlaps, tmp_path)
    write_json(run_id, "estimates.json", estimates, tmp_path)
    (dest / "workshop-memo.md").write_text("## Locked outcome\n", encoding="utf-8")
    code, result = validate_run(run_id, tmp_path, CLEAN_INVENTORY)
    assert code == 1
    assert any(f["code"] == "short_prose" and "devils_advocate" in f["path"] for f in result["failures"])


def test_unresolved_quantity_in_draft_exits_1(tmp_path: Path, complete_answers):
    run_id = _write_memo_run(tmp_path, complete_answers)
    write_approved(run_id, tmp_path)
    draft = render_to_run(run_id, tmp_path, TEMPLATES)
    draft.write_text(draft.read_text(encoding="utf-8") + "\n€12M\n", encoding="utf-8")
    code, result = validate_run(run_id, tmp_path, CLEAN_INVENTORY)
    assert code == 1
    assert any(f["code"] == "unresolved_quantity" for f in result["failures"])


def test_duplicate_new_short_override_exits_1(tmp_path: Path, complete_answers):
    complete_answers["duplicate_override"] = "too short"
    run_id = _write_memo_run(tmp_path, complete_answers)
    write_json(
        run_id,
        "overlaps.json",
        {"overlaps": [{"id": "ctl-1", "kind": "control", "title": "Holdout", "score": 0.9}]},
        tmp_path,
    )
    code, result = validate_run(run_id, tmp_path, CLEAN_INVENTORY)
    assert code == 1
    assert any(f["code"] == "duplicate_new" for f in result["failures"])


def test_memo_only_no_draft_exits_0(tmp_path: Path, complete_answers):
    run_id = _write_memo_run(tmp_path, complete_answers)
    code, result = validate_run(run_id, tmp_path, CLEAN_INVENTORY)
    assert code == 0
    assert result["stage"] == "memo"
    assert result["failures"] == []
    assert not (tmp_path / run_id / "draft.md").exists()
