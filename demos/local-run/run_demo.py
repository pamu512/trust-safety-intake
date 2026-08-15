from __future__ import annotations

import io
import json
import shutil
from contextlib import redirect_stdout
from pathlib import Path

from trust_intake.cli import main
from trust_intake.render import memo_sha

ROOT = Path(__file__).resolve().parents[2]
DEMO = Path(__file__).resolve().parent
PACKS = DEMO / "packs"
RUNS = DEMO / "runs"
INV_DIR = DEMO / "inventory"
INV = INV_DIR / "product-inventory.yaml"
PILE = DEMO / "pile"

PACK_ORDER = (
    ("promo-stacking", "Promo stacking cap for foodora"),
    ("account-takeover", "Account takeover step-up for foodpanda"),
    ("checkout-timeout", "Checkout timeout retry for yemeksepeti"),
)


def _flags(run_id: str) -> list[str]:
    return [
        "--run",
        run_id,
        "--runs-dir",
        str(RUNS),
        "--inventory",
        str(INV),
        "--templates",
        str(ROOT / "templates"),
    ]


def _setup() -> None:
    if RUNS.exists():
        shutil.rmtree(RUNS)
    if INV_DIR.exists():
        shutil.rmtree(INV_DIR)
    if PILE.exists():
        shutil.rmtree(PILE)
    RUNS.mkdir(parents=True)
    INV_DIR.mkdir(parents=True)
    shutil.copy(ROOT / "inventory" / "product-inventory.yaml", INV)
    PILE.mkdir(parents=True)


def _run_pack(name: str, title: str) -> str:
    pack = PACKS / name
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["init", "--title", title, "--runs-dir", str(RUNS)])
    if code:
        raise SystemExit(f"init failed for {name}: {code}")
    run_id = buf.getvalue().strip().splitlines()[-1]
    raw = json.loads((pack / "answers.json").read_text(encoding="utf-8"))
    raw["run_id"] = run_id
    (RUNS / run_id / "answers.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    flags = _flags(run_id)
    csv_path = pack / "loss.csv"
    if csv_path.is_file():
        parse_code = main(["parse", str(csv_path), *flags])
        if parse_code:
            raise SystemExit(f"parse failed for {name}: {parse_code}")
    for step in ("run",):
        step_code = main([step, *flags])
        if step_code:
            raise SystemExit(f"{step} failed for {name}: {step_code}")
    sha = memo_sha(run_id, RUNS)
    for cmd in (
        ["approve", *flags, "--confirm", sha],
        ["render", *flags],
        ["validate", *flags],
        ["decide", "--run", run_id, "--runs-dir", str(RUNS), "--inventory", str(INV)],
    ):
        step_code = main(cmd)
        if step_code:
            raise SystemExit(f"{cmd[0]} failed for {name}: {step_code}")
    shutil.copy(RUNS / run_id / "draft.md", PILE / f"{name}.md")
    print(f"OK {name} -> {run_id}")
    return run_id


def _triage() -> None:
    shutil.copy(PACKS / "account-takeover" / "ato.md", PILE / "account-takeover-copy.md")
    code = main(["triage", str(PILE), "--inventory", str(INV), "--markets", str(ROOT / "inventory" / "markets.yaml")])
    if code:
        raise SystemExit(f"triage failed: {code}")
    code = main(["decide", "--triage", str(PILE), "--inventory", str(INV)])
    if code:
        raise SystemExit(f"decide --triage failed: {code}")
    print("OK triage + decide")


def main_demo() -> None:
    _setup()
    for name, title in PACK_ORDER:
        _run_pack(name, title)
    _triage()
    print(f"runs: {RUNS}")
    print(f"inventory: {INV}")
    print(f"pile: {PILE}")


if __name__ == "__main__":
    main_demo()
