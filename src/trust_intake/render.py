from __future__ import annotations

import re
from pathlib import Path

from trust_intake.answers import PROSE_PATHS
from trust_intake.ledger import build_ledger
from trust_intake.run_store import read_json, run_dir

EACH_RE = re.compile(r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}", re.S)
VAR_RE = re.compile(r"\{\{\s*([^#/][^}]*?)\s*\}\}")
DOC_FILES = {
    "brd": "brd.md",
    "prd": "prd.md",
    "business-case": "business-case.md",
    "case-study": "case-study.md",
}


def _get(data: object, dotted: str):
    cur: object = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _plain_number(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return "" if value is None else str(value)


def _format_eur(value: float) -> str:
    sign = "-" if value < 0 else ""
    av = abs(value)
    if av >= 1_000_000:
        n, suffix = av / 1_000_000, "M"
    elif av >= 1000:
        n, suffix = av / 1000, "k"
    else:
        n, suffix = av, ""
    body = str(int(n)) if n == int(n) else f"{n:.2f}".rstrip("0").rstrip(".")
    return f"{sign}€{body}{suffix}"


def format_ledger_value(row: dict) -> str:
    name = str(row.get("name") or "")
    unit = row.get("unit")
    value = row.get("value")
    if value is None:
        return ""
    if unit == "EUR":
        return _format_eur(float(value))
    if unit == "%" or name in ("rate", "trend"):
        return f"{float(value) * 100:.2f}%"
    return _plain_number(value)


def _ledger_row(ledger: list[dict] | None, name: str) -> dict | None:
    for row in ledger or []:
        if row.get("name") == name:
            return row
    return None


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_stringify(v) for v in value)
    return str(value)


def _resolve(ctx: dict, path: str) -> str:
    parts = path.split(".")
    if parts[0] == "ledger" and len(parts) == 2:
        row = _ledger_row(ctx.get("ledger"), parts[1])
        return format_ledger_value(row) if row else ""
    cur: object = ctx
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return ""
        cur = cur[part]
    return _stringify(cur)


def _render_vars(text: str, ctx: dict) -> str:
    return VAR_RE.sub(lambda m: _resolve(ctx, m.group(1).strip()), text)


def render_template(text: str, ctx: dict) -> str:
    def each(match: re.Match[str]) -> str:
        key, body = match.group(1), match.group(2)
        items = ctx.get(key) or []
        chunks: list[str] = []
        for item in items:
            row = dict(item) if isinstance(item, dict) else {"value": item}
            if key == "ledger":
                row["validate_flag"] = "Validate" if row.get("source") == "ESTIMATE" else ""
                row["value"] = _plain_number(row.get("value"))
            chunks.append(_render_vars(body, {**ctx, **row}))
        return "".join(chunks)

    return _render_vars(EACH_RE.sub(each, text), ctx)


def _require_prose(answers: dict) -> None:
    for path in PROSE_PATHS:
        val = _get(answers, path)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"required prose empty: {path}")


def _context(answers: dict, facts: dict, overlaps: dict, estimates: dict, ledger: list[dict]) -> dict:
    return {
        "answers": answers,
        "facts": facts,
        "overlaps": overlaps,
        "estimates": estimates,
        "ledger": ledger,
        "options": answers.get("options") or [],
    }


def _load_template(templates_dir: Path, name: str) -> str:
    path = Path(templates_dir) / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _render(template_name: str, answers: dict, facts: dict, overlaps: dict, estimates: dict, ledger: list[dict], templates_dir: Path) -> str:
    _require_prose(answers)
    src = _load_template(templates_dir, template_name)
    return render_template(src, _context(answers, facts, overlaps, estimates, ledger))


def render_memo(
    answers: dict,
    facts: dict,
    overlaps: dict,
    estimates: dict,
    ledger: list[dict],
    templates_dir: Path = Path("templates"),
    run_id: str | None = None,
    runs_dir: Path | None = None,
) -> str:
    text = _render("workshop-memo.md", answers, facts, overlaps, estimates, ledger, templates_dir)
    if run_id is not None and runs_dir is not None:
        dest = run_dir(run_id, runs_dir) / "workshop-memo.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    return text


def render_doc(
    doc_type: str,
    answers: dict,
    facts: dict,
    overlaps: dict,
    estimates: dict,
    ledger: list[dict],
    templates_dir: Path = Path("templates"),
) -> str:
    if doc_type not in DOC_FILES:
        raise ValueError(f"unknown doc_type: {doc_type}")
    return _render(DOC_FILES[doc_type], answers, facts, overlaps, estimates, ledger, templates_dir)


def write_approved(run_id: str, runs_dir: Path) -> Path:
    path = run_dir(run_id, runs_dir) / "APPROVED"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def is_approved(run_id: str, runs_dir: Path) -> bool:
    return (run_dir(run_id, runs_dir) / "APPROVED").is_file()


def render_to_run(run_id: str, runs_dir: Path, templates_dir: Path = Path("templates")) -> Path:
    if not is_approved(run_id, runs_dir):
        raise PermissionError("APPROVED missing")
    answers = read_json(run_id, "answers.json", runs_dir)
    facts = read_json(run_id, "facts.json", runs_dir)
    overlaps = read_json(run_id, "overlaps.json", runs_dir)
    estimates = read_json(run_id, "estimates.json", runs_dir)
    ledger = build_ledger(facts, answers, estimates)
    text = render_doc(answers["doc_type"], answers, facts, overlaps, estimates, ledger, templates_dir)
    dest = run_dir(run_id, runs_dir) / "draft.md"
    dest.write_text(text, encoding="utf-8")
    return dest
