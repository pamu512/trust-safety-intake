from pathlib import Path

from trust_intake.cli import main


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
