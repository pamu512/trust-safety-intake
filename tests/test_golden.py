from pathlib import Path
import json
import shutil

from trust_intake.cli import main
from trust_intake.ledger import build_ledger, unresolved_quantities
from trust_intake.render import memo_sha
from trust_intake.run_store import read_json

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "refund-abuse"
PROMO = ROOT / "examples" / "promo-stacking"
BAD = ROOT / "tests" / "fixtures" / "bad-no-advocate"
TEMPLATES = ROOT / "templates"
INVENTORY = ROOT / "inventory" / "product-inventory.yaml"
RUN_ID = "golden-refund-abuse"
REFUND_SLOTS = {"volume": 10000, "rate": 0.12, "euro_impact": 2500000}
PROMO_SLOTS = {"volume": 50000, "rate": 0.08, "euro_impact": 1800000}


def _flags(tmp_path: Path, run_id: str) -> list[str]:
    return [
        "--run",
        run_id,
        "--runs-dir",
        str(tmp_path),
        "--templates",
        str(TEMPLATES),
        "--inventory",
        str(INVENTORY),
    ]


def _stage(src: Path, tmp_path: Path, run_id: str) -> Path:
    answers = src / "answers.json"
    csv_path = src / "loss.csv"
    assert answers.is_file(), f"missing {answers}"
    assert csv_path.is_file(), f"missing {csv_path}"
    dest = tmp_path / run_id
    dest.mkdir(parents=True)
    shutil.copy(answers, dest / "answers.json")
    shutil.copy(csv_path, dest / "loss.csv")
    return dest


def _pipeline(tmp_path: Path, run_id: str, csv_path: Path) -> list[int]:
    flags = _flags(tmp_path, run_id)
    codes = [
        main(["parse", str(csv_path), *flags]),
        main(["match", *flags]),
        main(["extrapolate", *flags]),
        main(["memo", *flags]),
    ]
    try:
        codes.append(main(["approve", *flags, "--confirm", memo_sha(run_id, tmp_path)]))
    except FileNotFoundError:
        codes.append(2)
    codes.extend(
        [
            main(["render", *flags]),
            main(["validate", *flags]),
        ]
    )
    return codes


def test_golden_refund_abuse_validate_exits_0(tmp_path: Path):
    dest = _stage(GOLDEN, tmp_path, RUN_ID)
    codes = _pipeline(tmp_path, RUN_ID, dest / "loss.csv")
    assert codes[-1] == 0
    draft = (tmp_path / RUN_ID / "draft.md").read_text(encoding="utf-8")
    assert "## Problem" in draft
    assert "Devil's advocate" in draft
    assert "€12M" not in draft
    facts = read_json(RUN_ID, "facts.json", tmp_path)
    answers = read_json(RUN_ID, "answers.json", tmp_path)
    estimates = read_json(RUN_ID, "estimates.json", tmp_path)
    leftover = unresolved_quantities(draft, build_ledger(facts, answers, estimates))
    assert leftover == []


def _slot_values(answers: dict) -> dict:
    metrics = answers.get("needed_metrics") or {}
    return {slot: (metrics.get(slot) or {}).get("value") for slot in ("volume", "rate", "euro_impact")}


def _init_parse_run_approve_render_validate(tmp_path: Path, src: Path, title: str) -> tuple[str, list[int]]:
    # Distinct from _pipeline: real init (printed id) then parse → run → approve → render → validate.
    code = main(["init", "--title", title, "--runs-dir", str(tmp_path)])
    run_id = next(p.name for p in tmp_path.iterdir() if p.is_dir())
    dest = tmp_path / run_id
    answers = json.loads((src / "answers.json").read_text(encoding="utf-8"))
    answers["run_id"] = run_id
    (dest / "answers.json").write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
    shutil.copy(src / "loss.csv", dest / "loss.csv")
    flags = _flags(tmp_path, run_id)
    codes = [code, main(["parse", str(dest / "loss.csv"), *flags]), main(["run", *flags])]
    try:
        codes.append(main(["approve", *flags, "--confirm", memo_sha(run_id, tmp_path)]))
    except FileNotFoundError:
        codes.append(2)
    codes.extend([main(["render", *flags]), main(["validate", *flags])])
    return run_id, codes


def test_golden_promo_stacking_validate_exits_0(tmp_path: Path):
    refund = json.loads((GOLDEN / "answers.json").read_text(encoding="utf-8"))
    promo = json.loads((PROMO / "answers.json").read_text(encoding="utf-8"))
    assert promo["title"] != refund["title"]
    assert promo["journey"] == "promo"
    assert refund["journey"] == "claims-cancel"
    assert promo["brands"] == ["foodora"]
    assert refund["brands"] == ["foodpanda"]
    assert promo["success"]["metric"] == "promo-stack-rate"
    assert refund["success"]["metric"] == "refund-abuse-rate"
    assert promo["favorite_option_id"] == "hard-cap"
    assert refund["favorite_option_id"] == "holdout"
    assert _slot_values(promo) == PROMO_SLOTS
    assert _slot_values(refund) == REFUND_SLOTS
    assert promo["devils_advocate"] != refund["devils_advocate"]
    assert "hard cap" in promo["devils_advocate"]["why_fails"].lower()
    assert "holdout" not in promo["devils_advocate"]["why_fails"].lower()
    promo_csv = (PROMO / "loss.csv").read_text(encoding="utf-8")
    refund_csv = (GOLDEN / "loss.csv").read_text(encoding="utf-8")
    assert promo_csv != refund_csv
    assert "orders" in promo_csv
    assert "claims" not in promo_csv

    run_id, codes = _init_parse_run_approve_render_validate(
        tmp_path, PROMO, promo["title"]
    )
    assert codes[-1] == 0
    draft = (tmp_path / run_id / "draft.md").read_text(encoding="utf-8")
    facts = read_json(run_id, "facts.json", tmp_path)
    answers = read_json(run_id, "answers.json", tmp_path)
    estimates = read_json(run_id, "estimates.json", tmp_path)
    ledger = build_ledger(facts, answers, estimates)
    leftover = unresolved_quantities(draft, ledger)
    assert leftover == []
    by_name = {row["name"]: row for row in ledger}
    assert by_name["volume"]["value"] == PROMO_SLOTS["volume"]
    assert by_name["volume"]["unit"] == "orders"
    assert by_name["rate"]["value"] == PROMO_SLOTS["rate"]
    assert by_name["euro_impact"]["value"] == PROMO_SLOTS["euro_impact"]
    interview_vals = {by_name[slot]["value"] for slot in REFUND_SLOTS}
    assert interview_vals.isdisjoint(REFUND_SLOTS.values())
    derived_names = {row["name"] for row in (facts.get("derived") or [])}
    assert "loss.orders.sum" in derived_names
    assert "loss.claims.sum" not in derived_names
    assert answers["journey"] == "promo"
    assert answers["favorite_option_id"] == "hard-cap"
    assert "promo-stack-rate" in draft
    assert "Hard stack cap" in draft
    assert "Holdout + policy" not in draft
    assert "weekly review already catches the loudest stacks" in draft


def test_bad_no_advocate_validate_exits_1(tmp_path: Path):
    dest = _stage(BAD, tmp_path, "bad-no-advocate")
    _pipeline(tmp_path, "bad-no-advocate", dest / "loss.csv")
    assert main(["validate", *_flags(tmp_path, "bad-no-advocate")]) == 1
