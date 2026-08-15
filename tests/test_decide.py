import json
import shutil
from pathlib import Path

from trust_intake.cli import main
from trust_intake.decide import decide_run, decide_triage
from trust_intake.inventory_lint import lint_inventory, load_inventory
from trust_intake.render import memo_sha, render_memo
from trust_intake.run_store import init_run, write_json

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SEED = ROOT / "inventory" / "product-inventory.yaml"


def _approved_run(tmp_path: Path, complete_answers: dict, **updates) -> str:
    dest = init_run(complete_answers["title"], runs_dir=tmp_path)
    run_id = dest.name
    answers = dict(complete_answers)
    answers.update(updates)
    answers["run_id"] = run_id
    facts = {"derived": []}
    overlaps = {"overlaps": []}
    estimates = {"estimates": []}
    write_json(run_id, "answers.json", answers, tmp_path)
    write_json(run_id, "facts.json", facts, tmp_path)
    write_json(run_id, "overlaps.json", overlaps, tmp_path)
    write_json(run_id, "estimates.json", estimates, tmp_path)
    from trust_intake.ledger import build_ledger

    render_memo(
        answers,
        facts,
        overlaps,
        estimates,
        build_ledger(facts, answers, estimates),
        TEMPLATES,
        run_id=run_id,
        runs_dir=tmp_path,
    )
    assert main(["approve", "--run", run_id, "--runs-dir", str(tmp_path), "--confirm", memo_sha(run_id, tmp_path)]) == 0
    return run_id


def test_decide_run_new_upserts_doc(tmp_path: Path, complete_answers):
    inv_path = tmp_path / "product-inventory.yaml"
    shutil.copy(SEED, inv_path)
    run_id = _approved_run(tmp_path, complete_answers, doc_action="new")
    code = main(
        ["decide", "--run", run_id, "--runs-dir", str(tmp_path), "--inventory", str(inv_path)]
    )
    assert code == 0
    data = load_inventory(inv_path)
    assert lint_inventory(data) == []
    doc_id = f"doc-{run_id}"
    found = next(d for d in data["docs"] if d["id"] == doc_id)
    assert found["status"] == "approved"
    assert found["title"] == complete_answers["title"]
    decision = json.loads((tmp_path / run_id / "decision.json").read_text())
    assert decision["source"] == "run"
    assert decision["locked"]["option_id"] == "holdout"
    assert inv_path.with_suffix(".md").is_file()


def test_decide_run_without_approve_exits_1(tmp_path: Path, complete_answers):
    dest = init_run("X", runs_dir=tmp_path)
    write_json(dest.name, "answers.json", complete_answers, tmp_path)
    inv = load_inventory(SEED)
    code, _decision, _inv, failures = decide_run(dest.name, tmp_path, inv)
    assert code == 1
    assert any(f["code"] == "missing_approved" for f in failures)


def test_decide_run_amend_updates_target(tmp_path: Path, complete_answers):
    inv = load_inventory(SEED)
    run_id = _approved_run(
        tmp_path,
        complete_answers,
        doc_action="amend",
        amend_target_id="doc-ex-1",
        title="Repeat claimant holdout",
    )
    code, decision, updated, failures = decide_run(run_id, tmp_path, inv)
    assert code == 0
    assert failures == []
    target = next(d for d in updated["docs"] if d["id"] == "doc-ex-1")
    assert target["title"] == "Repeat claimant holdout"
    assert target["status"] == "approved"
    assert decision["inventory_writes"][0]["id"] == "doc-ex-1"


def test_decide_run_kill_sets_killed(tmp_path: Path, complete_answers):
    inv = load_inventory(SEED)
    run_id = _approved_run(tmp_path, complete_answers, doc_action="kill", amend_target_id="doc-ex-1")
    code, _decision, updated, failures = decide_run(run_id, tmp_path, inv)
    assert code == 0
    assert failures == []
    assert next(d for d in updated["docs"] if d["id"] == "doc-ex-1")["status"] == "killed"


def test_decide_run_do_nothing_writes_none(tmp_path: Path, complete_answers):
    inv = load_inventory(SEED)
    run_id = _approved_run(
        tmp_path,
        complete_answers,
        doc_action="new",
        favorite_option_id="do-nothing",
        recommendation={
            "option_id": "do-nothing",
            "argument": "The locked outcome is a Finance-grade savings proof; only waiting is honest.",
        },
    )
    before = len(inv["docs"])
    code, decision, updated, failures = decide_run(run_id, tmp_path, inv)
    assert code == 0
    assert failures == []
    assert decision["inventory_writes"] == [{"op": "none", "id": None}]
    assert len(updated["docs"]) == before


def test_decide_triage_survivor_and_high_priority(tmp_path: Path):
    inv = load_inventory(SEED)
    folder = tmp_path / "pile"
    folder.mkdir()
    (folder / "triage.json").write_text(
        json.dumps(
            {
                "cards": [
                    {
                        "id": "wide",
                        "title": "Cross-brand promo abuse",
                        "brands": ["foodora", "foodpanda"],
                        "markets": ["SG", "HK"],
                        "journey": "promo",
                        "labels": ["high-priority", "unify"],
                        "reasons": [],
                        "cluster_id": "cluster-wide",
                        "path": "wide.md",
                    },
                    {
                        "id": "thin",
                        "title": "Thin copy",
                        "brands": ["foodora"],
                        "markets": ["SG"],
                        "journey": "promo",
                        "labels": ["deprioritise", "unify"],
                        "reasons": ["thin"],
                        "cluster_id": "cluster-wide",
                        "path": "thin.md",
                    },
                    {
                        "id": "solo",
                        "title": "Germany refund SLA",
                        "brands": ["foodora"],
                        "markets": ["DE"],
                        "journey": "claims-cancel",
                        "labels": ["high-priority"],
                        "reasons": [],
                        "path": "solo.md",
                    },
                    {
                        "id": "tiny",
                        "title": "Small promo",
                        "brands": ["foodora"],
                        "markets": ["SG"],
                        "journey": "promo",
                        "labels": ["deprioritise"],
                        "reasons": ["thin"],
                        "path": "tiny.md",
                    },
                ],
                "clusters": [
                    {"id": "cluster-wide", "survivor": "wide", "members": ["wide", "thin"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    inv["docs"].append(
        {
            "id": "doc-thin",
            "type": "brd",
            "title": "Thin copy",
            "status": "open",
            "journey": "promo",
            "brands": ["foodora"],
            "link": "",
        }
    )
    code, decision, updated, failures = decide_triage(folder, inv)
    assert code == 0
    assert failures == []
    ids = {d["id"]: d for d in updated["docs"]}
    assert ids["doc-wide"]["status"] == "open"
    assert ids["doc-solo"]["status"] == "open"
    assert ids["doc-thin"]["status"] == "killed"
    assert "doc-tiny" not in ids
    assert lint_inventory(updated) == []
    assert decision["source"] == "triage"


def test_decide_triage_missing_json_exits_2(tmp_path: Path):
    code, _d, _i, failures = decide_triage(tmp_path, load_inventory(SEED))
    assert code == 2
    assert any(f["code"] == "missing_file" for f in failures)
