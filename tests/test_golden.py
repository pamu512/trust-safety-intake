from pathlib import Path
import shutil

from trust_intake.cli import main
from trust_intake.ledger import build_ledger, unresolved_quantities
from trust_intake.run_store import read_json

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "refund-abuse"
BAD = ROOT / "tests" / "fixtures" / "bad-no-advocate"
TEMPLATES = ROOT / "templates"
INVENTORY = ROOT / "inventory" / "product-inventory.yaml"
RUN_ID = "golden-refund-abuse"


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
    return [
        main(["parse", str(csv_path), *flags]),
        main(["match", *flags]),
        main(["extrapolate", *flags]),
        main(["memo", *flags]),
        main(["approve", *flags]),
        main(["render", *flags]),
        main(["validate", *flags]),
    ]


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


def test_bad_no_advocate_validate_exits_1(tmp_path: Path):
    dest = _stage(BAD, tmp_path, "bad-no-advocate")
    _pipeline(tmp_path, "bad-no-advocate", dest / "loss.csv")
    assert main(["validate", *_flags(tmp_path, "bad-no-advocate")]) == 1
