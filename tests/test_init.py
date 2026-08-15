from datetime import datetime
from pathlib import Path

from trust_intake.run_store import init_run, new_run_id, read_json


def test_new_run_id_slug_and_timestamp():
    rid = new_run_id("Refund abuse holdout", now=datetime(2026, 8, 15, 9, 30, 0))
    assert rid == "20260815-093000-refund-abuse-holdout"


def test_init_run_writes_answers_skeleton(tmp_path: Path):
    path = init_run("Refund abuse holdout", runs_dir=tmp_path)
    answers = read_json(path.name, "answers.json", runs_dir=tmp_path)
    assert answers["title"] == "Refund abuse holdout"
    assert answers["run_id"] == path.name
    assert answers["decision"] is None
    assert set(answers["needed_metrics"]) == {
        "volume",
        "rate",
        "euro_impact",
        "trend",
        "baseline",
        "cx_fp_cost",
    }
    assert (path / "answers.json").is_file()
