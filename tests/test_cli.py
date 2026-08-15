from pathlib import Path

from trust_intake.cli import main
from trust_intake.render import memo_sha
from trust_intake.run_store import write_json

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
INVENTORY = ROOT / "inventory" / "product-inventory.yaml"


def test_init_prints_run_id(tmp_path: Path, capsys):
    code = main(["init", "--title", "Refund abuse holdout", "--runs-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert (tmp_path / out / "answers.json").is_file()


def test_render_without_approve_exits_1(tmp_path: Path):
    main(["init", "--title", "X", "--runs-dir", str(tmp_path)])
    run_id = next(tmp_path.iterdir()).name
    code = main(["render", "--run", run_id, "--runs-dir", str(tmp_path)])
    assert code == 1


def test_inventory_lint_ok():
    assert main(["inventory-lint", "--inventory", "inventory/product-inventory.yaml"]) == 0


def test_parse_missing_file_exits_2(tmp_path: Path, capsys):
    main(["init", "--title", "X", "--runs-dir", str(tmp_path)])
    run_id = next(tmp_path.iterdir()).name
    missing = tmp_path / "nope.csv"
    code = main(["parse", str(missing), "--run", run_id, "--runs-dir", str(tmp_path)])
    assert code == 2
    err = capsys.readouterr().err
    assert err.strip()
    assert "nope.csv" in err


def test_inventory_lint_missing_exits_2(tmp_path: Path):
    assert main(["inventory-lint", "--inventory", str(tmp_path / "missing.yaml")]) == 2


def test_inventory_lint_bad_markets_exits_1(tmp_path: Path):
    markets = tmp_path / "markets.yaml"
    markets.write_text("markets:\n  - {id: SG}\n  - {id: SG}\n", encoding="utf-8")
    assert (
        main(
            [
                "inventory-lint",
                "--inventory",
                str(INVENTORY),
                "--markets",
                str(markets),
            ]
        )
        == 1
    )


def test_inventory_lint_missing_markets_skips(tmp_path: Path):
    assert (
        main(
            [
                "inventory-lint",
                "--inventory",
                str(INVENTORY),
                "--markets",
                str(tmp_path / "nope.yaml"),
            ]
        )
        == 0
    )


def test_triage_bad_markets_exits_2(tmp_path: Path):
    markets = tmp_path / "markets.yaml"
    markets.write_text("markets:\n  - {id: SG}\n  - {id: SG}\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\nfoodora\n", encoding="utf-8")
    assert main(["triage", str(tmp_path), "--markets", str(markets)]) == 2


def test_triage_empty_folder_exits_1(tmp_path: Path):
    assert main(["triage", str(tmp_path)]) == 1


def test_triage_missing_folder_exits_2(tmp_path: Path):
    assert main(["triage", str(tmp_path / "nope")]) == 2


def test_triage_scores_md(tmp_path: Path):
    (tmp_path / "a.md").write_text(
        "# Repeat claimant static control\nfoodpanda Singapore\n€2.5M\nclaims-cancel\n"
    )
    (tmp_path / "b.md").write_text(
        "# Repeat claimant static rule\nfoodpanda Hong Kong\n€1M\nclaims-cancel\n"
    )
    assert main(["triage", str(tmp_path)]) == 0
    assert (tmp_path / "triage.json").is_file()
    assert (tmp_path / "triage.md").is_file()
    md = (tmp_path / "triage.md").read_text()
    assert "High priority" in md or "Unify" in md or "Deprioritise" in md


def test_run_without_file_then_render_exits_0(tmp_path: Path, complete_answers):
    assert main(["init", "--title", "Holdout for refunds", "--runs-dir", str(tmp_path)]) == 0
    run_id = next(p.name for p in tmp_path.iterdir() if p.is_dir())
    write_json(run_id, "answers.json", complete_answers, tmp_path)
    flags = [
        "--run",
        run_id,
        "--runs-dir",
        str(tmp_path),
        "--templates",
        str(TEMPLATES),
        "--inventory",
        str(INVENTORY),
    ]
    assert main(["run", *flags]) == 0
    assert main(["approve", *flags]) == 1
    assert main(["approve", *flags, "--confirm", memo_sha(run_id, tmp_path)]) == 0
    assert main(["render", *flags]) == 0
