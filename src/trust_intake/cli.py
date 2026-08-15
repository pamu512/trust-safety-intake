from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trust_intake.answers import validate_answers
from trust_intake.extrapolate import extrapolate
from trust_intake.inventory_lint import lint_inventory, load_inventory
from trust_intake.inventory_render import render_inventory_md
from trust_intake.ledger import build_ledger
from trust_intake.markets import lint_markets, load_markets
from trust_intake.match_inventory import match
from trust_intake.parse_table import parse_table
from trust_intake.render import is_approved, render_memo, render_to_run, write_approved
from trust_intake.run_store import init_run, read_json, write_json
from trust_intake.triage import render_triage_md, run_triage
from trust_intake.validate_draft import validate_run


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _emit(failures: list[dict]) -> None:
    for item in failures:
        print(json.dumps(item, ensure_ascii=False), file=sys.stderr)


def _read_optional(run_id: str, name: str, runs_dir: Path, default: dict) -> dict:
    try:
        return read_json(run_id, name, runs_dir)
    except FileNotFoundError:
        return default


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit([_fail("usage", "", message)])
        self.exit(2)


def _build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--runs-dir", default="runs")
    parent.add_argument("--inventory", default="inventory/product-inventory.yaml")
    parent.add_argument("--markets", default="inventory/markets.yaml")
    parent.add_argument("--templates", default="templates")

    parser = _Parser(prog="trust-intake")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_p = sub.add_parser("init", parents=[parent])
    init_p.add_argument("--title", required=True)

    parse_p = sub.add_parser("parse", parents=[parent])
    parse_p.add_argument("file")
    parse_p.add_argument("--run", required=True)

    for name in ("match", "extrapolate", "memo", "approve", "render", "validate"):
        p = sub.add_parser(name, parents=[parent])
        p.add_argument("--run", required=True)

    run_p = sub.add_parser("run", parents=[parent])
    run_p.add_argument("--run", required=True)
    run_p.add_argument("--file")

    triage_p = sub.add_parser("triage", parents=[parent])
    triage_p.add_argument("folder")
    triage_p.add_argument("--min-euro", type=float, default=100000)

    sub.add_parser("inventory-lint", parents=[parent])
    sub.add_parser("inventory-render", parents=[parent])
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    dest = init_run(args.title, Path(args.runs_dir))
    print(dest.name)
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        facts = parse_table(path)
    except FileNotFoundError:
        _emit([_fail("missing_file", str(path), f"missing {path}")])
        return 2
    except (OSError, ValueError) as exc:
        _emit([_fail("unreadable_file", str(path), str(exc))])
        return 2
    write_json(args.run, "facts.json", facts, Path(args.runs_dir))
    return 0


def _cmd_match(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir)
    answers = read_json(args.run, "answers.json", runs_dir)
    inventory = load_inventory(Path(args.inventory))
    write_json(args.run, "overlaps.json", match(answers, inventory), runs_dir)
    return 0


def _cmd_extrapolate(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir)
    answers = read_json(args.run, "answers.json", runs_dir)
    facts = _read_optional(args.run, "facts.json", runs_dir, {"tables": [], "derived": []})
    write_json(args.run, "estimates.json", extrapolate(answers, facts), runs_dir)
    return 0


def _cmd_memo(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir)
    answers = read_json(args.run, "answers.json", runs_dir)
    failures = validate_answers(answers)
    if failures:
        _emit(failures)
        return 1
    facts = _read_optional(args.run, "facts.json", runs_dir, {"tables": [], "derived": []})
    overlaps = _read_optional(args.run, "overlaps.json", runs_dir, {"overlaps": []})
    estimates = _read_optional(args.run, "estimates.json", runs_dir, {"estimates": []})
    ledger = build_ledger(facts, answers, estimates)
    try:
        render_memo(
            answers,
            facts,
            overlaps,
            estimates,
            ledger,
            Path(args.templates),
            run_id=args.run,
            runs_dir=runs_dir,
        )
    except ValueError as exc:
        _emit([_fail("empty_prose", "", str(exc))])
        return 1
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    write_approved(args.run, Path(args.runs_dir))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir)
    if not is_approved(args.run, runs_dir):
        _emit([_fail("missing_approved", "APPROVED", "APPROVED missing")])
        return 1
    try:
        render_to_run(args.run, runs_dir, Path(args.templates))
    except PermissionError as exc:
        _emit([_fail("missing_approved", "APPROVED", str(exc))])
        return 1
    except ValueError as exc:
        _emit([_fail("empty_prose", "", str(exc))])
        return 1
    except FileNotFoundError as exc:
        _emit([_fail("missing_file", str(exc), str(exc))])
        return 2
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    inventory = load_inventory(Path(args.inventory))
    code, payload = validate_run(args.run, Path(args.runs_dir), inventory)
    failures = payload.get("failures") or []
    if failures:
        _emit(failures)
    return code


def _cmd_run(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir)
    if args.file:
        code = _cmd_parse(args)
        if code:
            return code
    else:
        if not (runs_dir / args.run / "facts.json").is_file():
            write_json(args.run, "facts.json", {"tables": [], "derived": []}, runs_dir)
    for step in (_cmd_match, _cmd_extrapolate, _cmd_memo):
        code = step(args)
        if code:
            return code
    return 0


def _cmd_inventory_lint(args: argparse.Namespace) -> int:
    path = Path(args.inventory)
    try:
        data = load_inventory(path)
    except FileNotFoundError:
        _emit([_fail("missing_file", str(path), f"missing {path}")])
        return 2
    except (OSError, ValueError) as exc:
        _emit([_fail("unreadable_file", str(path), str(exc))])
        return 2
    failures = lint_inventory(data)
    markets_path = Path(args.markets)
    if markets_path.is_file():
        try:
            raw = load_inventory(markets_path)
        except (OSError, ValueError) as exc:
            _emit([_fail("unreadable_file", str(markets_path), str(exc))])
            return 2
        failures.extend(lint_markets(raw))
    if failures:
        _emit(failures)
        return 1
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        _emit([_fail("missing_file", str(folder), f"missing {folder}")])
        return 2
    inventory = load_inventory(Path(args.inventory))
    markets = load_markets(Path(args.markets))
    code, payload = run_triage(folder, inventory, markets, args.min_euro)
    (folder / "triage.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "triage.md").write_text(render_triage_md(payload), encoding="utf-8")
    return code


def _cmd_inventory_render(args: argparse.Namespace) -> int:
    path = Path(args.inventory)
    data = load_inventory(path)
    dest = path.with_suffix(".md")
    dest.write_text(render_inventory_md(data), encoding="utf-8")
    return 0


_COMMANDS = {
    "init": _cmd_init,
    "parse": _cmd_parse,
    "match": _cmd_match,
    "extrapolate": _cmd_extrapolate,
    "memo": _cmd_memo,
    "approve": _cmd_approve,
    "render": _cmd_render,
    "validate": _cmd_validate,
    "run": _cmd_run,
    "inventory-lint": _cmd_inventory_lint,
    "inventory-render": _cmd_inventory_render,
    "triage": _cmd_triage,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    try:
        return _COMMANDS[args.cmd](args)
    except FileNotFoundError as exc:
        _emit([_fail("missing_file", str(exc.filename or exc), str(exc))])
        return 2
    except FileExistsError as exc:
        _emit([_fail("exists", str(exc.filename or exc), str(exc))])
        return 2
    except OSError as exc:
        _emit([_fail("io_error", str(exc.filename or exc), str(exc))])
        return 2
