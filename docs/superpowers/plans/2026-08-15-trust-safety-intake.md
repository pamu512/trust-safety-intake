# Trust Safety Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a finished `trust-intake` factory plus a Cursor/LLM skill that interviews Pandora authors and refuses to write a BRD/PRD/business case/case study except through that factory.

**Architecture:** The agent writes `answers.json` prose only. A Python CLI owns init, CSV/XLSX parse, inventory overlap, named-method extrapolate, template render, approve gate, number ledger, and hard validate. Each intake is a `runs/<id>/` folder. Drafts cannot exist without `APPROVED`.

**Tech Stack:** Python 3.11+, pytest, PyYAML, openpyxl. Stdlib `difflib` for title overlap. No other dependencies.

## Global Constraints

- Python 3.11+; dependencies are only PyYAML and openpyxl.
- Package import: `trust_intake`. CLI name: `trust-intake`.
- Inventory source of truth: `inventory/product-inventory.yaml`. Markdown is generated. Do not edit `.md` by hand.
- Brands: `foodora`, `foodpanda`, `yemeksepeti`. Journeys: `account`, `promo`, `checkout`, `claims-cancel`, `payout`, `cross-journey`.
- Overlap score = 0.4 journey exact + 0.3 brand overlap + 0.3 `difflib` title ratio. Threshold `>= 0.72`.
- Extrapolate methods only: `run-rate`, `share-of-parent`, `last-period-carry`, `peer-brand-ratio`. No silent guesses.
- Numbers in docs only via `{{ledger.name}}`. Quantity tokens: `€`/`EUR`, `%`, or number + `orders|GMV|bps|FTE|flags|claims|payouts`.
- Prose fields minimum 40 characters. `do-nothing` option required. Devil’s advocate four fields required.
- `render` requires `APPROVED`. `run` stops after `memo`.
- No confidential Pandora pack numbers. Golden example is anonymized.
- Exit codes: `0` ok, `1` gate failure, `2` usage/IO error.
- Spec: `docs/superpowers/specs/2026-08-15-trust-safety-intake-design.md`.

## File map

| File | Responsibility |
| --- | --- |
| `src/trust_intake/run_store.py` | Run id, folder create, JSON read/write, `APPROVED` |
| `src/trust_intake/answers.py` | Empty skeleton + schema/prose validation |
| `src/trust_intake/inventory_lint.py` | Load + lint YAML inventory |
| `src/trust_intake/inventory_render.py` | YAML → markdown tables |
| `src/trust_intake/parse_table.py` | CSV/XLSX → `facts.json` |
| `src/trust_intake/match_inventory.py` | Overlap scoring → `overlaps.json` |
| `src/trust_intake/ledger.py` | Union facts/answers/estimates; scan quantity tokens |
| `src/trust_intake/extrapolate.py` | Fill null `needed_metrics` with named methods |
| `src/trust_intake/render.py` | Fill workshop memo + four doc templates |
| `src/trust_intake/validate_draft.py` | Memo-stage and draft-stage gates |
| `src/trust_intake/cli.py` | argparse subcommands |
| `templates/*.md` | Memo, BRD, PRD, business-case, case-study |
| `inventory/product-inventory.yaml` | Seed inventory |
| `skills/trust-intake/SKILL.md` | Agent contract |
| `examples/refund-abuse/` | Golden run that must exit 0 |

---

### Task 1: Package + run store (`init`)

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/trust_intake/__init__.py`
- Create: `src/trust_intake/run_store.py`
- Create: `src/trust_intake/answers.py`
- Test: `tests/test_init.py`

**Interfaces:**
- Consumes: nothing
- Produces: `new_run_id(title: str, now: datetime | None = None) -> str`; `init_run(title: str, runs_dir: Path) -> Path`; `run_dir(run_id: str, runs_dir: Path) -> Path`; `read_json(run_id: str, name: str, runs_dir: Path) -> dict`; `write_json(run_id: str, name: str, data: dict, runs_dir: Path) -> Path`; `empty_answers(run_id: str, title: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_init.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_init.py -v`  
Expected: FAIL with `ModuleNotFoundError: trust_intake` or collection error.

- [ ] **Step 3: Write minimal implementation**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "trust-intake"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0", "openpyxl>=3.1"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
trust-intake = "trust_intake.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
runs/
```

`src/trust_intake/__init__.py` — empty.

`src/trust_intake/answers.py`:

```python
from __future__ import annotations

NEEDED_SLOTS = (
    "volume",
    "rate",
    "euro_impact",
    "trend",
    "baseline",
    "cx_fp_cost",
)


def empty_metric() -> dict:
    return {"value": None, "unit": None}


def empty_answers(run_id: str, title: str) -> dict:
    return {
        "run_id": run_id,
        "title": title,
        "decision": None,
        "success": {"metric": None, "direction": None, "target": None},
        "approvers": [],
        "brands": [],
        "journey": None,
        "already_ships": "",
        "doc_action": None,
        "amend_target_id": None,
        "duplicate_override": None,
        "elapsed_fraction": None,
        "shares": {},
        "doc_type": None,
        "needed_metrics": {slot: empty_metric() for slot in NEEDED_SLOTS},
        "numbers_from_author": [],
        "options": [],
        "favorite_option_id": None,
        "devils_advocate": {
            "why_fails": "",
            "who_loses": "",
            "cannot_measure": "",
            "why_not_live_control": "",
        },
        "recommendation": {"option_id": None, "argument": ""},
    }
```

`src/trust_intake/run_store.py`:

```python
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from trust_intake.answers import empty_answers


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def new_run_id(title: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slugify(title)}"


def run_dir(run_id: str, runs_dir: Path) -> Path:
    return runs_dir / run_id


def write_json(run_id: str, name: str, data: dict, runs_dir: Path) -> Path:
    path = run_dir(run_id, runs_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(run_id: str, name: str, runs_dir: Path) -> dict:
    path = run_dir(run_id, runs_dir) / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def init_run(title: str, runs_dir: Path, now: datetime | None = None) -> Path:
    run_id = new_run_id(title, now=now)
    dest = run_dir(run_id, runs_dir)
    dest.mkdir(parents=True, exist_ok=False)
    write_json(run_id, "answers.json", empty_answers(run_id, title), runs_dir)
    return dest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e ".[dev]" && python -m pytest tests/test_init.py -v`  
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src/trust_intake/__init__.py src/trust_intake/run_store.py src/trust_intake/answers.py tests/test_init.py
git commit -m "$(cat <<'EOF'
feat: add run store and answers skeleton

EOF
)"
```

---

### Task 2: Answers completeness validation

**Files:**
- Modify: `src/trust_intake/answers.py`
- Test: `tests/test_answers.py`

**Interfaces:**
- Consumes: `empty_answers`
- Produces: `validate_answers(answers: dict) -> list[dict]` where each dict is `{code, path, message}`; `PROSE_MIN = 40`; `expand_brands(brands: list[str]) -> list[str]` maps `all` → the three brands

- [ ] **Step 1: Write the failing test**

```python
# tests/test_answers.py
from trust_intake.answers import empty_answers, expand_brands, validate_answers


def _complete() -> dict:
    a = empty_answers("r1", "Holdout for refunds")
    a.update(
        {
            "decision": "ship",
            "success": {"metric": "refund-abuse-rate", "direction": "down", "target": "0.4%"},
            "approvers": ["finance"],
            "brands": ["foodpanda"],
            "journey": "claims-cancel",
            "already_ships": "Manual refund queue plus a static rule on repeat claimants in 30 days.",
            "doc_action": "new",
            "doc_type": "brd",
            "options": [
                {
                    "id": "do-nothing",
                    "title": "Keep the queue",
                    "summary": "Leave the existing refund queue and static rule unchanged for this quarter.",
                    "is_do_nothing": True,
                },
                {
                    "id": "holdout",
                    "title": "Holdout + policy",
                    "summary": "Ship a holdout on refund policy changes and measure net margin before scaling.",
                    "is_do_nothing": False,
                },
            ],
            "favorite_option_id": "holdout",
            "devils_advocate": {
                "why_fails": "Holdout may starve a market of refunds and spike NPS complaints in week one.",
                "who_loses": "Good customers who need a legitimate refund during the holdout window.",
                "cannot_measure": "True fraudster displacement will not show in ninety days of one brand.",
                "why_not_live_control": "The static repeat-claimant rule already covers the loudest pattern.",
            },
            "recommendation": {
                "option_id": "holdout",
                "argument": "The locked outcome is a Finance-grade savings proof; only a holdout produces that proof.",
            },
        }
    )
    a["needed_metrics"]["volume"] = {"value": 10000, "unit": "claims"}
    a["numbers_from_author"] = [{"name": "volume", "value": 10000, "unit": "claims", "source": "interview"}]
    return a


def test_complete_answers_have_no_failures():
    assert validate_answers(_complete()) == []


def test_short_prose_fails():
    a = _complete()
    a["already_ships"] = "a queue"
    fails = validate_answers(a)
    assert any(f["path"] == "already_ships" for f in fails)


def test_missing_do_nothing_fails():
    a = _complete()
    a["options"] = [o for o in a["options"] if not o["is_do_nothing"]]
    fails = validate_answers(a)
    assert any(f["code"] == "missing_do_nothing" for f in fails)


def test_expand_all_brands():
    assert expand_brands(["all"]) == ["foodora", "foodpanda", "yemeksepeti"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_answers.py -v`  
Expected: FAIL with `cannot import name validate_answers`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/trust_intake/answers.py`:

```python
BRANDS = ("foodora", "foodpanda", "yemeksepeti")
JOURNEYS = ("account", "promo", "checkout", "claims-cancel", "payout", "cross-journey")
DECISIONS = ("ship", "fund", "stop", "change-policy", "align")
DOC_ACTIONS = ("new", "amend", "kill")
DOC_TYPES = ("brd", "prd", "business-case", "case-study")
DIRECTIONS = ("up", "down", "hold")
PROSE_MIN = 40
PROSE_PATHS = (
    "already_ships",
    "devils_advocate.why_fails",
    "devils_advocate.who_loses",
    "devils_advocate.cannot_measure",
    "devils_advocate.why_not_live_control",
    "recommendation.argument",
)


def _get(data: dict, dotted: str):
    cur: object = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def expand_brands(brands: list[str]) -> list[str]:
    if "all" in brands:
        return list(BRANDS)
    return [b for b in brands if b in BRANDS]


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def validate_answers(answers: dict) -> list[dict]:
    fails: list[dict] = []
    required = (
        "run_id",
        "title",
        "decision",
        "success",
        "approvers",
        "brands",
        "journey",
        "already_ships",
        "doc_action",
        "doc_type",
        "needed_metrics",
        "options",
        "favorite_option_id",
        "devils_advocate",
        "recommendation",
    )
    for key in required:
        if key not in answers:
            fails.append(_fail("missing_key", key, f"missing {key}"))
    if fails:
        return fails
    if answers["decision"] not in DECISIONS:
        fails.append(_fail("bad_enum", "decision", "invalid decision"))
    if answers["journey"] not in JOURNEYS:
        fails.append(_fail("bad_enum", "journey", "invalid journey"))
    if answers["doc_action"] not in DOC_ACTIONS:
        fails.append(_fail("bad_enum", "doc_action", "invalid doc_action"))
    if answers["doc_type"] not in DOC_TYPES:
        fails.append(_fail("bad_enum", "doc_type", "invalid doc_type"))
    success = answers["success"]
    if not success.get("metric") or success.get("direction") not in DIRECTIONS:
        fails.append(_fail("bad_success", "success", "metric and direction required"))
    if not answers["approvers"]:
        fails.append(_fail("missing_approvers", "approvers", "at least one approver"))
    if not expand_brands(answers.get("brands") or []):
        fails.append(_fail("missing_brands", "brands", "at least one brand"))
    for path in PROSE_PATHS:
        val = _get(answers, path)
        if not isinstance(val, str) or len(val.strip()) < PROSE_MIN:
            fails.append(_fail("short_prose", path, f"{path} must be >= {PROSE_MIN} chars"))
    for opt in answers["options"]:
        if len(str(opt.get("summary") or "")) < PROSE_MIN:
            fails.append(_fail("short_prose", f"options.{opt.get('id')}.summary", "option summary too short"))
    if not any(o.get("is_do_nothing") for o in answers["options"]):
        fails.append(_fail("missing_do_nothing", "options", "one option must be do-nothing"))
    ids = {o.get("id") for o in answers["options"]}
    if answers["favorite_option_id"] not in ids:
        fails.append(_fail("bad_option", "favorite_option_id", "favorite not in options"))
    if answers["recommendation"].get("option_id") not in ids:
        fails.append(_fail("bad_option", "recommendation.option_id", "recommendation not in options"))
    if answers["doc_action"] == "new":
        override = answers.get("duplicate_override")
        # override checked later against overlaps; here only length if present
        if override is not None and len(str(override).strip()) < PROSE_MIN:
            fails.append(_fail("short_override", "duplicate_override", "override must be >= 40 chars"))
    return fails
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_answers.py -v`  
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/answers.py tests/test_answers.py
git commit -m "$(cat <<'EOF'
feat: validate complete answers schema

EOF
)"
```

---

### Task 3: Inventory lint + render

**Files:**
- Create: `src/trust_intake/inventory_lint.py`
- Create: `src/trust_intake/inventory_render.py`
- Create: `inventory/product-inventory.yaml`
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: brand/journey enums from `answers.py`
- Produces: `load_inventory(path: Path) -> dict`; `lint_inventory(data: dict) -> list[dict]`; `render_inventory_md(data: dict) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_inventory.py
from pathlib import Path

from trust_intake.inventory_lint import lint_inventory, load_inventory
from trust_intake.inventory_render import render_inventory_md


def _ok() -> dict:
    return {
        "brands": ["foodora", "foodpanda", "yemeksepeti"],
        "journeys": [
            "account",
            "promo",
            "checkout",
            "claims-cancel",
            "payout",
            "cross-journey",
        ],
        "stack": [{"id": "rules", "name": "Rules engine", "layer": "decisioning", "notes": ""}],
        "controls": [
            {
                "id": "ctl-refund-static",
                "name": "Repeat claimant rule",
                "type": "rule",
                "journey": "claims-cancel",
                "brands": ["foodpanda"],
                "status": "live",
                "owner": "ops",
                "related_docs": ["doc-ex-1"],
            }
        ],
        "docs": [
            {
                "id": "doc-ex-1",
                "type": "brd",
                "title": "Repeat claimant static rule",
                "status": "shipped",
                "journey": "claims-cancel",
                "brands": ["foodpanda"],
                "link": "",
            }
        ],
    }


def test_lint_clean():
    assert lint_inventory(_ok()) == []


def test_lint_duplicate_id():
    data = _ok()
    data["stack"].append({"id": "rules", "name": "dup", "layer": "x", "notes": ""})
    assert any(f["code"] == "duplicate_id" for f in lint_inventory(data))


def test_lint_dangling_related_docs():
    data = _ok()
    data["controls"][0]["related_docs"] = ["missing"]
    assert any(f["code"] == "dangling_related_docs" for f in lint_inventory(data))


def test_render_contains_tables():
    md = render_inventory_md(_ok())
    assert "| ctl-refund-static |" in md
    assert "| doc-ex-1 |" in md


def test_load_seed_file():
    data = load_inventory(Path("inventory/product-inventory.yaml"))
    assert lint_inventory(data) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_inventory.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation + seed YAML**

`inventory/product-inventory.yaml`:

```yaml
brands:
  - foodora
  - foodpanda
  - yemeksepeti
journeys:
  - account
  - promo
  - checkout
  - claims-cancel
  - payout
  - cross-journey
stack:
  - id: rules
    name: Rules engine
    layer: decisioning
    notes: Parameterize before new PRDs
  - id: ml-score
    name: ML risk score
    layer: decisioning
    notes: Maturity to map
  - id: sql-wh
    name: SQL warehouse
    layer: data
    notes: ""
  - id: looker
    name: Looker
    layer: reporting
    notes: ""
  - id: manual-inv
    name: Manual investigations
    layer: ops
    notes: ""
controls:
  - id: ctl-refund-static
    name: Repeat claimant rule
    type: rule
    journey: claims-cancel
    brands: [foodpanda]
    status: live
    owner: ops
    related_docs: [doc-ex-1]
docs:
  - id: doc-ex-1
    type: brd
    title: Repeat claimant static rule
    status: shipped
    journey: claims-cancel
    brands: [foodpanda]
    link: ""
```

`src/trust_intake/inventory_lint.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

from trust_intake.answers import BRANDS, JOURNEYS

CONTROL_TYPES = ("rule", "ml", "policy", "ops")
CONTROL_STATUS = ("live", "pilot", "planned", "retired")
DOC_TYPES = ("brd", "prd", "business-case", "case-study", "ticket")
DOC_STATUS = ("draft", "open", "approved", "shipped", "killed")


def load_inventory(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("inventory must be a mapping")
    return data


def lint_inventory(data: dict) -> list[dict]:
    fails: list[dict] = []
    for key in ("brands", "journeys", "stack", "controls", "docs"):
        if key not in data:
            fails.append({"code": "missing_key", "path": key, "message": f"missing {key}"})
    if fails:
        return fails
    if list(data["brands"]) != list(BRANDS):
        fails.append({"code": "bad_brands", "path": "brands", "message": "brands must be the three Pandora brands"})
    if list(data["journeys"]) != list(JOURNEYS):
        fails.append({"code": "bad_journeys", "path": "journeys", "message": "journeys enum mismatch"})
    ids: dict[str, str] = {}
    for group in ("stack", "controls", "docs"):
        for i, row in enumerate(data[group] or []):
            rid = row.get("id")
            path = f"{group}[{i}]"
            if not rid:
                fails.append({"code": "missing_id", "path": path, "message": "id required"})
                continue
            if rid in ids:
                fails.append({"code": "duplicate_id", "path": path, "message": f"duplicate id {rid}"})
            ids[rid] = group
    doc_ids = {d.get("id") for d in data["docs"] or []}
    for i, ctl in enumerate(data["controls"] or []):
        if ctl.get("type") not in CONTROL_TYPES:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].type", "message": "bad type"})
        if ctl.get("status") not in CONTROL_STATUS:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].status", "message": "bad status"})
        if ctl.get("journey") not in JOURNEYS:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].journey", "message": "bad journey"})
        for ref in ctl.get("related_docs") or []:
            if ref not in doc_ids:
                fails.append({"code": "dangling_related_docs", "path": f"controls[{i}].related_docs", "message": ref})
    for i, doc in enumerate(data["docs"] or []):
        if doc.get("type") not in DOC_TYPES:
            fails.append({"code": "bad_enum", "path": f"docs[{i}].type", "message": "bad type"})
        if doc.get("status") not in DOC_STATUS:
            fails.append({"code": "bad_enum", "path": f"docs[{i}].status", "message": "bad status"})
    return fails
```

`src/trust_intake/inventory_render.py`:

```python
from __future__ import annotations


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_inventory_md(data: dict) -> str:
    parts = ["# Product inventory", "", "Generated. Edit `product-inventory.yaml`.", ""]
    parts += ["## Stack", "", _table(["id", "name", "layer", "notes"], [[s["id"], s["name"], s["layer"], s.get("notes") or ""] for s in data["stack"]]), ""]
    parts += ["## Controls", "", _table(
        ["id", "name", "type", "journey", "brands", "status", "owner"],
        [[c["id"], c["name"], c["type"], c["journey"], ",".join(c["brands"]), c["status"], c["owner"]] for c in data["controls"]],
    ), ""]
    parts += ["## Docs", "", _table(
        ["id", "type", "title", "status", "journey", "brands"],
        [[d["id"], d["type"], d["title"], d["status"], d["journey"], ",".join(d["brands"])] for d in data["docs"]],
    ), ""]
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_inventory.py -v`  
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/inventory_lint.py src/trust_intake/inventory_render.py inventory/product-inventory.yaml tests/test_inventory.py
git commit -m "$(cat <<'EOF'
feat: lint and render product inventory

EOF
)"
```

---

### Task 4: Parse CSV and XLSX

**Files:**
- Create: `src/trust_intake/parse_table.py`
- Test: `tests/test_parse_table.py`

**Interfaces:**
- Consumes: file path
- Produces: `parse_table(path: Path) -> dict` with `tables[]` and `derived[]` as in the spec. Raises `OSError`/`ValueError` on unreadable files (CLI maps to exit 2).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_parse_table.py
from pathlib import Path

from openpyxl import Workbook

from trust_intake.parse_table import parse_table


def test_csv_totals_and_yoy(tmp_path: Path):
    p = tmp_path / "loss.csv"
    p.write_text(
        "period,brand,loss_eur\n2024-01-01,foodpanda,100\n2025-01-01,foodpanda,128\n",
        encoding="utf-8",
    )
    facts = parse_table(p)
    table = facts["tables"][0]
    assert table["row_count"] == 2
    assert table["totals"]["loss_eur"] == 228
    yoy = next(d for d in facts["derived"] if d["method"] == "yoy")
    assert yoy["value"] == 0.28
    assert yoy["source"] == "csv"


def test_xlsx_multisheet_and_empty_warning(tmp_path: Path):
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "loss"
    ws1.append(["period", "loss_eur"])
    ws1.append(["2025-01-01", 50])
    ws2 = wb.create_sheet("empty")
    ws2.append(["period", "loss_eur"])
    path = tmp_path / "t.xlsx"
    wb.save(path)
    facts = parse_table(path)
    names = {t["name"] for t in facts["tables"]}
    assert names == {"loss", "empty"}
    empty = next(t for t in facts["tables"] if t["name"] == "empty")
    assert any("empty" in w.lower() or "single" in w.lower() or "no rows" in w.lower() for w in empty["warnings"])


def test_bad_euro_text_warns(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text("period,loss_eur\n2025-01-01,not-a-number\n", encoding="utf-8")
    facts = parse_table(p)
    assert facts["tables"][0]["warnings"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parse_table.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation**

Write `src/trust_intake/parse_table.py` exactly:

```python
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

DATE_FMTS = ("%Y-%m-%d", "%Y-%m", "%d/%m/%Y")


def _parse_date(raw: str):
    text = raw.strip()
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_number(raw: str):
    text = raw.strip().replace(",", "").replace("€", "").replace("EUR", "").replace("%", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _looks_numeric(header: str, raw: str) -> bool:
    h = header.lower()
    return any(tok in h or tok in raw for tok in ("€", "eur", "%", "loss", "gmv", "rate"))


def _infer_type(header: str, values: list[str]) -> str:
    nonempty = [v for v in values if v.strip()]
    if nonempty and all(_parse_date(v) for v in nonempty):
        return "date"
    if nonempty and all(_parse_number(v) is not None for v in nonempty):
        return "number"
    if 0 < len(set(nonempty)) <= 12:
        return "category"
    return "text"


def _table_from_rows(name: str, headers: list[str], rows: list[list[str]]) -> tuple[dict, list[dict]]:
    warnings: list[str] = []
    if not rows:
        warnings.append("no rows")
    if len(rows) == 1:
        warnings.append("single row")
    cols = {h: [r[i] if i < len(r) else "" for r in rows] for i, h in enumerate(headers)}
    types = {h: _infer_type(h, cols[h]) for h in headers}
    totals: dict[str, float] = {}
    missingness: dict[str, float] = {}
    n = len(rows)
    for h in headers:
        vals = cols[h]
        miss = 0
        if types[h] == "number":
            nums = []
            for v in vals:
                num = _parse_number(v)
                if num is None:
                    miss += 1
                    if v.strip() or _looks_numeric(h, v):
                        warnings.append(f"unparsed number in {h}: {v!r}")
                else:
                    nums.append(num)
            totals[h] = sum(nums)
        elif types[h] == "date":
            miss = sum(1 for v in vals if not v.strip() or _parse_date(v) is None)
        else:
            miss = sum(1 for v in vals if not v.strip())
        missingness[h] = (miss / n) if n else 0.0
    date_col = next((h for h, t in types.items() if t == "date"), None)
    num_cols = [h for h, t in types.items() if t == "number"]
    series: list[dict] = []
    if date_col and num_cols and n:
        grouped: dict[str, dict[str, float]] = {}
        for r in rows:
            rec = dict(zip(headers, r))
            dt = _parse_date(rec.get(date_col, ""))
            if not dt:
                continue
            period = dt.strftime("%Y-%m-%d")
            bucket = grouped.setdefault(period, {c: 0.0 for c in num_cols})
            for c in num_cols:
                num = _parse_number(rec.get(c, ""))
                if num is not None:
                    bucket[c] += num
        series = [{"period": p, "values": grouped[p]} for p in sorted(grouped)]
    split_col = next((h for h in headers if "brand" in h.lower() or "market" in h.lower()), None)
    splits: list[dict] = []
    if split_col and num_cols:
        grouped_s: dict[str, dict[str, float]] = {}
        for r in rows:
            rec = dict(zip(headers, r))
            key = rec.get(split_col, "") or "unknown"
            bucket = grouped_s.setdefault(key, {c: 0.0 for c in num_cols})
            for c in num_cols:
                num = _parse_number(rec.get(c, ""))
                if num is not None:
                    bucket[c] += num
        splits = [{"key": k, "values": grouped_s[k]} for k in grouped_s]
    derived: list[dict] = []
    for c, total in totals.items():
        derived.append({"name": f"{name}.{c}.sum", "value": total, "unit": None, "source": "csv", "method": "sum"})
    if len(series) >= 2:
        old, new = series[-2], series[-1]
        for c in num_cols:
            ov, nv = old["values"][c], new["values"][c]
            if ov:
                derived.append({"name": f"{name}.{c}.pop", "value": (nv - ov) / ov, "unit": None, "source": "csv", "method": "pop"})
        by_year: dict[int, dict] = {}
        for item in series:
            year = int(item["period"][:4])
            by_year[year] = item
        years = sorted(by_year)
        if len(years) >= 2:
            y0, y1 = years[-2], years[-1]
            if y1 == y0 + 1:
                for c in num_cols:
                    ov, nv = by_year[y0]["values"][c], by_year[y1]["values"][c]
                    if ov:
                        derived.append({"name": f"{name}.{c}.yoy", "value": (nv - ov) / ov, "unit": None, "source": "csv", "method": "yoy"})
    if splits:
        parent = {c: sum(s["values"][c] for s in splits) for c in num_cols}
        for s in splits:
            for c in num_cols:
                if parent[c]:
                    derived.append({"name": f"{name}.{s['key']}.{c}.share", "value": s["values"][c] / parent[c], "unit": None, "source": "csv", "method": "split-share"})
    table = {
        "name": name,
        "columns": [{"name": h, "type": types[h]} for h in headers],
        "row_count": n,
        "totals": totals,
        "missingness": missingness,
        "series": series,
        "splits": splits,
        "warnings": warnings,
    }
    return table, derived


def _read_csv(path: Path) -> list[tuple[str, list[str], list[list[str]]]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        headers = next(reader, None)
        if not headers:
            return [(path.stem, [], [])]
        rows = [row for row in reader]
        return [(path.stem, headers, rows)]


def _read_xlsx(path: Path) -> list[tuple[str, list[str], list[list[str]]]]:
    wb = load_workbook(path, data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        rows_iter = ws.iter_rows(values_only=True)
        first = next(rows_iter, None)
        if not first:
            out.append((ws.title, [], []))
            continue
        headers = [str(c) if c is not None else "" for c in first]
        rows = []
        for row in rows_iter:
            rows.append(["" if c is None else str(c) for c in row])
        out.append((ws.title, headers, rows))
    return out


def parse_table(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        sheets = _read_csv(path)
    elif suffix in {".xlsx", ".xlsm"}:
        sheets = _read_xlsx(path)
    else:
        raise ValueError(f"unsupported file type: {suffix}")
    tables = []
    derived: list[dict] = []
    for name, headers, rows in sheets:
        table, der = _table_from_rows(name, headers, rows)
        tables.append(table)
        derived.extend(der)
    return {"tables": tables, "derived": derived}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_parse_table.py -v`  
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/parse_table.py tests/test_parse_table.py
git commit -m "$(cat <<'EOF'
feat: parse CSV and XLSX into facts

EOF
)"
```

---

### Task 5: Inventory match

**Files:**
- Create: `src/trust_intake/match_inventory.py`
- Test: `tests/test_match.py`

**Interfaces:**
- Consumes: `expand_brands`; inventory `controls` + `docs`
- Produces: `score_overlap(title: str, journey: str, brands: list[str], item: dict) -> float`; `match(answers: dict, inventory: dict) -> dict` with `overlaps: [{id, kind, title, score}]` and `threshold: 0.72`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_match.py
from trust_intake.match_inventory import match, score_overlap

INV = {
    "controls": [
        {
            "id": "ctl-refund-static",
            "name": "Repeat claimant rule",
            "journey": "claims-cancel",
            "brands": ["foodpanda"],
        }
    ],
    "docs": [
        {
            "id": "doc-ex-1",
            "title": "Repeat claimant static rule",
            "journey": "claims-cancel",
            "brands": ["foodpanda"],
        }
    ],
}


def test_same_journey_brand_similar_title_overlaps():
    answers = {
        "title": "Repeat claimant static control",
        "journey": "claims-cancel",
        "brands": ["foodpanda"],
    }
    out = match(answers, INV)
    assert any(o["score"] >= 0.72 for o in out["overlaps"])


def test_different_journey_no_overlap():
    answers = {
        "title": "Repeat claimant static control",
        "journey": "promo",
        "brands": ["foodpanda"],
    }
    out = match(answers, INV)
    assert all(o["score"] < 0.72 for o in out["overlaps"])


def test_score_weights():
    item = {"title": "Repeat claimant static rule", "name": "Repeat claimant static rule", "journey": "claims-cancel", "brands": ["foodpanda"]}
    s = score_overlap("Repeat claimant static rule", "claims-cancel", ["foodpanda"], item)
    assert s == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_match.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation**

```python
# src/trust_intake/match_inventory.py
from __future__ import annotations

import difflib

from trust_intake.answers import expand_brands

THRESHOLD = 0.72


def _title(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "")


def score_overlap(title: str, journey: str, brands: list[str], item: dict) -> float:
    journey_score = 1.0 if item.get("journey") == journey else 0.0
    item_brands = set(item.get("brands") or [])
    author_brands = set(expand_brands(brands))
    if not item_brands or not author_brands:
        brand_score = 0.0
    else:
        brand_score = len(item_brands & author_brands) / len(item_brands | author_brands)
    title_score = difflib.SequenceMatcher(None, title.lower(), _title(item).lower()).ratio()
    return 0.4 * journey_score + 0.3 * brand_score + 0.3 * title_score


def match(answers: dict, inventory: dict) -> dict:
    title = answers["title"]
    journey = answers["journey"]
    brands = answers.get("brands") or []
    overlaps = []
    for kind, rows in (("control", inventory.get("controls") or []), ("doc", inventory.get("docs") or [])):
        for item in rows:
            s = score_overlap(title, journey, brands, item)
            overlaps.append(
                {
                    "id": item.get("id"),
                    "kind": kind,
                    "title": _title(item),
                    "score": round(s, 4),
                }
            )
    overlaps.sort(key=lambda o: o["score"], reverse=True)
    return {
        "threshold": THRESHOLD,
        "overlaps": [o for o in overlaps if o["score"] >= THRESHOLD],
        "scored": overlaps,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_match.py -v`  
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/match_inventory.py tests/test_match.py
git commit -m "$(cat <<'EOF'
feat: score inventory overlaps

EOF
)"
```

---

### Task 6: Number ledger

**Files:**
- Create: `src/trust_intake/ledger.py`
- Test: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `facts.json`, `answers.json`, `estimates.json`
- Produces: `build_ledger(facts: dict, answers: dict, estimates: dict) -> list[dict]` each `{name, value, unit, source}`; `scan_quantities(text: str) -> list[tuple[str, float]]`; `unresolved_quantities(text: str, ledger: list[dict]) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ledger.py
from trust_intake.ledger import build_ledger, scan_quantities, unresolved_quantities


def test_build_unions_three_sources():
    facts = {"derived": [{"name": "loss.sum", "value": 228, "unit": "EUR", "source": "csv", "method": "sum"}]}
    answers = {"numbers_from_author": [{"name": "volume", "value": 10000, "unit": "claims", "source": "interview"}]}
    estimates = {"estimates": [{"name": "euro_impact", "value": 2500000, "unit": "EUR", "source": "ESTIMATE"}]}
    names = {r["name"] for r in build_ledger(facts, answers, estimates)}
    assert names == {"loss.sum", "volume", "euro_impact"}


def test_scan_ignores_ninety_day():
    tokens = scan_quantities("In 90-day window refunds are €2.5M at 12% of claims.")
    values = {v for _, v in tokens}
    assert 2_500_000 in values
    assert 0.12 in values
    assert 90 not in values


def test_unresolved_extra_euro():
    ledger = [{"name": "euro_impact", "value": 2_500_000, "unit": "EUR", "source": "interview"}]
    leftover = unresolved_quantities("Savings of €2.5M plus a stray €12M.", ledger)
    assert leftover == ["€12M"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ledger.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation**

Write `src/trust_intake/ledger.py` exactly:

```python
from __future__ import annotations

import re

UNIT_WORDS = ("orders", "GMV", "bps", "FTE", "flags", "claims", "payouts")
EUR_RE = re.compile(r"(?:€|EUR)\s*([\d,]+(?:\.\d+)?)([kKmMbB])?", re.I)
PCT_RE = re.compile(r"(?<![\d-])(\d+(?:\.\d+)?)%")
UNIT_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s+(" + "|".join(UNIT_WORDS) + r")\b")
SKIP_RE = re.compile(r"90[- ]day", re.I)


def _suffix(mult: str | None) -> float:
    if not mult:
        return 1.0
    return {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[mult.lower()]


def build_ledger(facts: dict, answers: dict, estimates: dict) -> list[dict]:
    rows: list[dict] = []
    for item in facts.get("derived") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "csv"})
    for item in answers.get("numbers_from_author") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "interview"})
    for item in (estimates or {}).get("estimates") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "ESTIMATE"})
    return rows


def scan_quantities(text: str) -> list[tuple[str, float]]:
    if SKIP_RE.search(text):
        text_for_pct = SKIP_RE.sub(" ", text)
    else:
        text_for_pct = text
    found: list[tuple[str, float]] = []
    for m in EUR_RE.finditer(text):
        found.append((m.group(0).strip(), float(m.group(1).replace(",", "")) * _suffix(m.group(2))))
    for m in PCT_RE.finditer(text_for_pct):
        found.append((m.group(0), float(m.group(1)) / 100.0))
    for m in UNIT_RE.finditer(text):
        found.append((m.group(0), float(m.group(1).replace(",", ""))))
    return found


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 * max(1.0, abs(b))


def unresolved_quantities(text: str, ledger: list[dict]) -> list[str]:
    values = [float(r["value"]) for r in ledger]
    leftover = []
    for token, val in scan_quantities(text):
        if not any(_close(val, lv) for lv in values):
            leftover.append(token)
    return leftover
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ledger.py -v`  
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/ledger.py tests/test_ledger.py
git commit -m "$(cat <<'EOF'
feat: number ledger and quantity scan

EOF
)"
```

---

### Task 7: Extrapolate

**Files:**
- Create: `src/trust_intake/extrapolate.py`
- Test: `tests/test_extrapolate.py`

**Interfaces:**
- Consumes: `build_ledger`; `needed_metrics` null slots
- Produces: `extrapolate(answers: dict, facts: dict) -> dict` with `estimates: list[dict]` and `unknown: list[str]`

Each estimate: `{name, value, unit, source: ESTIMATE, method, inputs, range: {low, high}}`.

Ranges: run-rate ±20%, share-of-parent ±25%, last-period-carry ±30%, peer-brand-ratio ±35%.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extrapolate.py
from trust_intake.extrapolate import extrapolate


def test_run_rate_half_year():
    answers = {
        "needed_metrics": {
            "volume": {"value": None, "unit": "claims"},
            "rate": {"value": 0.1, "unit": None},
            "euro_impact": {"value": None, "unit": "EUR"},
            "trend": {"value": None, "unit": None},
            "baseline": {"value": None, "unit": None},
            "cx_fp_cost": {"value": None, "unit": None},
        },
        "elapsed_fraction": 0.5,
        "numbers_from_author": [
            {"name": "partial_euro_impact", "value": 1_000_000, "unit": "EUR", "source": "interview"}
        ],
        "shares": {},
        "brands": ["foodpanda"],
    }
    facts = {"derived": [], "tables": []}
    # map: if euro_impact null and partial_euro_impact + elapsed_fraction exist, run-rate
    out = extrapolate(answers, facts)
    est = next(e for e in out["estimates"] if e["name"] == "euro_impact")
    assert est["method"] == "run-rate"
    assert est["value"] == 2_000_000
    assert est["range"]["low"] == 1_600_000
    assert est["range"]["high"] == 2_400_000
    assert est["source"] == "ESTIMATE"


def test_refuse_when_no_method():
    answers = {
        "needed_metrics": {
            "volume": {"value": None, "unit": "claims"},
            "rate": {"value": None, "unit": None},
            "euro_impact": {"value": None, "unit": "EUR"},
            "trend": {"value": None, "unit": None},
            "baseline": {"value": None, "unit": None},
            "cx_fp_cost": {"value": None, "unit": None},
        },
        "elapsed_fraction": None,
        "numbers_from_author": [],
        "shares": {},
        "brands": ["foodpanda"],
    }
    out = extrapolate(answers, {"derived": [], "tables": []})
    assert out["estimates"] == []
    assert "volume" in out["unknown"]
    assert "euro_impact" in out["unknown"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_extrapolate.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation**

Write `src/trust_intake/extrapolate.py` exactly:

```python
from __future__ import annotations

from trust_intake.answers import NEEDED_SLOTS
from trust_intake.ledger import build_ledger

RANGES = {
    "run-rate": 0.20,
    "share-of-parent": 0.25,
    "last-period-carry": 0.30,
    "peer-brand-ratio": 0.35,
}

COLUMN_TO_SLOT = (
    (("loss", "euro", "eur"), "euro_impact"),
    (("volume", "claim"), "volume"),
    (("rate", "pct", "fp"), "rate"),
)


def _ledger_map(answers: dict, facts: dict) -> dict[str, dict]:
    rows = build_ledger(facts, answers, {"estimates": []})
    return {r["name"]: r for r in rows}


def _range(value: float, method: str) -> dict:
    delta = RANGES[method]
    return {"low": value * (1 - delta), "high": value * (1 + delta)}


def _estimate(name: str, value: float, unit: str | None, method: str, inputs: list[str]) -> dict:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "source": "ESTIMATE",
        "method": method,
        "inputs": inputs,
        "range": _range(value, method),
    }


def _slot_from_column(col: str) -> str | None:
    low = col.lower()
    for keys, slot in COLUMN_TO_SLOT:
        if any(k in low for k in keys):
            return slot
    return None


def extrapolate(answers: dict, facts: dict) -> dict:
    ledger = _ledger_map(answers, facts)
    estimates: list[dict] = []
    unknown: list[str] = []
    elapsed = answers.get("elapsed_fraction")
    shares = answers.get("shares") or {}
    brands = answers.get("brands") or []
    for slot in NEEDED_SLOTS:
        metric = (answers.get("needed_metrics") or {}).get(slot) or {}
        if metric.get("value") is not None:
            continue
        unit = metric.get("unit")
        partial = ledger.get(f"partial_{slot}")
        if partial and elapsed and 0 < float(elapsed) <= 1:
            value = float(partial["value"]) / float(elapsed)
            estimates.append(_estimate(slot, value, unit or partial.get("unit"), "run-rate", [partial["name"], "elapsed_fraction"]))
            continue
        parent = ledger.get(f"parent_{slot}")
        share = shares.get(slot)
        if parent and share and 0 < float(share) <= 1:
            value = float(parent["value"]) * float(share)
            estimates.append(_estimate(slot, value, unit or parent.get("unit"), "share-of-parent", [parent["name"], f"shares.{slot}"]))
            continue
        carried = None
        for table in facts.get("tables") or []:
            series = table.get("series") or []
            if not series:
                continue
            last = series[-1]["values"]
            for col, val in last.items():
                if _slot_from_column(col) == slot:
                    carried = (f"{table['name']}.{col}", val, unit)
        if carried:
            estimates.append(_estimate(slot, float(carried[1]), carried[2], "last-period-carry", [carried[0]]))
            continue
        peer_done = False
        for brand in brands:
            for name, row in ledger.items():
                if name == f"{slot}_{brand}":
                    continue
                if not name.startswith(f"{slot}_"):
                    continue
                peer = name.split("_", 1)[1]
                gmv_a = ledger.get(f"gmv_{brand}")
                gmv_p = ledger.get(f"gmv_{peer}")
                if gmv_a and gmv_p and float(gmv_p["value"]):
                    value = float(row["value"]) * float(gmv_a["value"]) / float(gmv_p["value"])
                    estimates.append(_estimate(slot, value, unit, "peer-brand-ratio", [name, gmv_a["name"], gmv_p["name"]]))
                    peer_done = True
                    break
            if peer_done:
                break
        if peer_done:
            continue
        unknown.append(slot)
    return {"estimates": estimates, "unknown": unknown}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_extrapolate.py -v`  
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/extrapolate.py tests/test_extrapolate.py
git commit -m "$(cat <<'EOF'
feat: named-method extrapolation

EOF
)"
```

---

### Task 8: Templates + render (memo and four docs)

**Files:**
- Create: `templates/workshop-memo.md`
- Create: `templates/brd.md`
- Create: `templates/prd.md`
- Create: `templates/business-case.md`
- Create: `templates/case-study.md`
- Create: `src/trust_intake/render.py`
- Test: `tests/test_render.py`
- Test: `tests/conftest.py` (shared complete answers fixture)

**Interfaces:**
- Consumes: answers, facts, overlaps, estimates, ledger
- Produces: `render_memo(...) -> str`; `render_doc(doc_type: str, ...) -> str`; `write_approved(run_id, runs_dir) -> Path`; `is_approved(run_id, runs_dir) -> bool`. `render_doc` raises `PermissionError` if `APPROVED` is missing when writing via `render_to_run`.

Placeholder syntax: `{{answers.title}}`, `{{ledger.volume}}`, `{{#each options}}...{{/each}}` — implement a tiny renderer in `render.py` (no Jinja). Support `{{#each}}`, dotted paths, and `{{ledger.NAME}}` which prints the formatted value from the ledger.

- [ ] **Step 1: Write templates and failing tests**

Shared head in every template (copy verbatim into all five files, then add the body):

```markdown
# {{answers.title}}

## Locked outcome
- Decision: {{answers.decision}}
- 90-day success: {{answers.success.metric}} {{answers.success.direction}} {{answers.success.target}}
- Approvers: {{answers.approvers}}

## Assumptions
| Claim | Source | Validate |
| --- | --- | --- |
{{#each ledger}}
| {{name}} = {{value}} {{unit}} | {{source}} | {{validate_flag}} |
{{/each}}

## Options
{{#each options}}
- {{id}}: {{title}} — {{summary}}
{{/each}}

## Devil's advocate
- Why it fails: {{answers.devils_advocate.why_fails}}
- Who loses: {{answers.devils_advocate.who_loses}}
- Cannot measure in 90 days: {{answers.devils_advocate.cannot_measure}}
- Why not the live control: {{answers.devils_advocate.why_not_live_control}}

## Recommendation
{{answers.recommendation.argument}}
```

BRD extra:

```markdown
## Problem
{{answers.already_ships}}

## Business requirements
- Requirement text must be testable. Amend target: {{answers.amend_target_id}}

## Metrics
- Primary: {{answers.success.metric}}

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with override.
```

PRD extra: `## Solution`, `## Journeys`, `## In scope`, `## Out of scope`, `## Acceptance criteria`, `## Non-goals`.  
Business case extra: `## Cost`, `## Impact`, `## Options comparison`, `## Ask`.  
Case study extra: `## Before`, `## Intervention`, `## After`.

`tests/test_render.py` must assert each rendered doc contains those extra headings, contains `Devil's advocate`, contains a do-nothing option id, and formats `{{ledger.volume}}` as a number from the ledger — not as the raw placeholder.

Also test `render_to_run` without `APPROVED` raises `PermissionError`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write `render.py`**

- Load templates from a `templates_dir: Path` argument (default `Path("templates")`).
- `write_approved` writes an empty file `APPROVED`.
- `render_to_run` writes `draft.md` only if `APPROVED` exists.
- `render_memo` always allowed; writes `workshop-memo.md`.
- If a required prose field is empty, raise `ValueError`.
- Format ledger EUR as `€X` / `€Xk` / `€XM` when unit is EUR; percents as `{value*100:.2f}%` when unit is `%` or name is `rate`/`trend`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates src/trust_intake/render.py tests/test_render.py tests/conftest.py
git commit -m "$(cat <<'EOF'
feat: render workshop memo and four doc types

EOF
)"
```

---

### Task 9: Validate (memo-stage and draft-stage)

**Files:**
- Create: `src/trust_intake/validate_draft.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `validate_answers`, `lint_inventory`, `unresolved_quantities`, `build_ledger`, `match` / `overlaps.json`
- Produces: `validate_run(run_id: str, runs_dir: Path, inventory: dict) -> tuple[int, dict]`  
  Exit `1` on any failure. `validation.json` = `{stage: memo|draft, failures: [{code, path, message}]}`.

Fail when:

1. `validate_answers` non-empty
2. no do-nothing (also covered by answers)
3. devil’s advocate empty (also covered)
4. `doc_action=new` and `overlaps.json` has overlaps and override missing or < 40 chars
5. `workshop-memo.md` missing
6. quantity token in memo (and draft if present) not on ledger
7. any estimate missing `method`/`inputs`/`range`
8. draft-stage: `draft.md` exists without `APPROVED`, or required headings for `doc_type` missing
9. `lint_inventory` non-empty
10. favorite/recommendation option ids bad (also covered)

- [ ] **Step 1: Write the failing test**

Use a temp run folder.

- Golden-shaped complete run → exit 0, stage `draft` after writing draft + APPROVED.
- Missing devil’s advocate → exit 1, code from answers.
- Draft text containing `€12M` not on ledger → exit 1, code `unresolved_quantity`.
- `doc_action=new`, overlap present, override `too short` → exit 1, code `duplicate_new`.
- Memo only, no draft → stage `memo`, exit 0 if otherwise clean.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validate.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write `validate_draft.py`**

Write `validation.json` into the run folder every time.

Required headings by type:

- brd: `## Problem`, `## Business requirements`, `## Metrics`, `## Non-goals`
- prd: `## Solution`, `## Journeys`, `## In scope`, `## Out of scope`, `## Acceptance criteria`, `## Non-goals`
- business-case: `## Cost`, `## Impact`, `## Options comparison`, `## Ask`
- case-study: `## Before`, `## Intervention`, `## After`

Plus shared: `## Locked outcome`, `## Assumptions`, `## Options`, `## Devil's advocate`, `## Recommendation`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validate.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/validate_draft.py tests/test_validate.py
git commit -m "$(cat <<'EOF'
feat: hard-fail validate for memo and draft

EOF
)"
```

---

### Task 10: CLI

**Files:**
- Create: `src/trust_intake/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: every module above
- Produces: `main(argv: list[str] | None = None) -> int`

Subcommands from the spec: `init`, `parse`, `match`, `extrapolate`, `memo`, `approve`, `render`, `validate`, `run`, `inventory-lint`, `inventory-render`.

Global flags: `--runs-dir` (default `runs`), `--inventory` (default `inventory/product-inventory.yaml`), `--templates` (default `templates`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write `cli.py`**

- `argparse` with subparsers.
- `init` prints run id to stdout.
- `parse` writes `facts.json`; missing file → exit 2.
- `match` reads answers + inventory, writes `overlaps.json`.
- `extrapolate` writes `estimates.json`.
- `memo` requires `validate_answers` empty enough to render; writes `workshop-memo.md`.
- `approve` writes `APPROVED`.
- `render` requires `APPROVED` else exit 1.
- `validate` writes `validation.json` and returns the exit code from `validate_run`.
- `run` = parse (if `--file`) → match → extrapolate → memo. Does not approve or render.
- `inventory-render` writes `inventory/product-inventory.md` next to the yaml.
- Print failure list as JSON lines to stderr on exit 1/2.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat: trust-intake CLI

EOF
)"
```

---

### Task 11: Golden example `examples/refund-abuse`

**Files:**
- Create: `examples/refund-abuse/answers.json`
- Create: `examples/refund-abuse/loss.csv`
- Create: `examples/refund-abuse/README.md`
- Test: `tests/test_golden.py`

**Interfaces:**
- Consumes: CLI
- Produces: a scripted run that ends with `validate` exit 0

- [ ] **Step 1: Write the failing test**

`tests/test_golden.py` copies `examples/refund-abuse/answers.json` and `loss.csv` into a temp runs dir under a known id `golden-refund-abuse`, writes a complete answers file (anonymized Brand X numbers: 10_000 claims, €2.5M, 12% rate), runs parse → match → extrapolate → memo → approve → render → validate via `main(...)`.

Assert validate exit 0.  
Assert `draft.md` contains `## Problem` and `Devil's advocate`.  
Assert `draft.md` does not contain `€12M`.  
Assert every `€` / `%` token in `draft.md` resolves on the ledger.

Also keep a second fixture directory `tests/fixtures/bad-no-advocate/` used only in this test file: same as golden but empty `why_fails` → validate exit 1.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_golden.py -v`  
Expected: FAIL (example files missing or validate not wired).

- [ ] **Step 3: Write the golden files**

Anonymized only. Brands may be `foodpanda` (real brand codes are in the inventory enum; euros and volumes are fake). Title: `Refund holdout for repeat claimants`. Journey: `claims-cancel`. `doc_action`: `amend` targeting `doc-ex-1` so overlap does not require override. `doc_type`: `brd`. Include do-nothing + holdout options and full devil’s advocate / recommendation prose (>= 40 chars).

`loss.csv`:

```csv
period,brand,loss_eur,claims
2024-01-01,foodpanda,2000000,8000
2025-01-01,foodpanda,2500000,10000
```

`examples/refund-abuse/README.md` — exact commands:

```
pip install -e ".[dev]"
trust-intake init --title "Refund holdout for repeat claimants"
# copy answers.json into the printed run folder, then:
trust-intake parse examples/refund-abuse/loss.csv --run <id>
trust-intake run --run <id>
trust-intake approve --run <id>
trust-intake render --run <id>
trust-intake validate --run <id>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_golden.py tests/test_validate.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/refund-abuse tests/test_golden.py tests/fixtures
git commit -m "$(cat <<'EOF'
test: golden refund-abuse run exits 0

EOF
)"
```

---

### Task 12: Skill + README

**Files:**
- Create: `skills/trust-intake/SKILL.md`
- Create: `skills/trust-intake/references/interview.md`
- Create: `skills/trust-intake/references/extrapolation.md`
- Create: `README.md`
- Create: `inventory/product-inventory.md` via `trust-intake inventory-render`

**Interfaces:**
- Consumes: CLI contract from Task 10
- Produces: agent-facing skill that forbids freehand drafts

- [ ] **Step 1: Write SKILL.md**

Frontmatter description (trigger only, no workflow summary):

```yaml
---
name: trust-intake
description: Use when someone at Pandora Trust & Safety wants a BRD, PRD, business case, or case study; when an ask is unclear and an outcome must be locked first; when a request might duplicate an existing control or BRD; or when numbers or trends are missing and a CSV/XLSX or extrapolation is needed.
---
```

Body must include, verbatim in spirit:

- Read this skill before interviewing. Ask one question at a time.
- Do not write `draft.md` or a freehand BRD/PRD.
- Do not skip `init`, `parse`, `match`, `extrapolate`, `memo`, `approve`, `render`, `validate`.
- Do not treat inventory as complete; still ask what ships today.
- After locking the outcome, argue for it. Before recommending, attack it.
- Overlap + new BRD → recommend amend. Write new only with override.
- Link `references/interview.md` and `references/extrapolation.md`.
- Copy the interview order from spec §7.
- Copy the CLI commands from spec §9.

`interview.md` = the 14 questions with enums.  
`extrapolation.md` = the four methods table and refuse rule.

`README.md` = what the repo is, install, golden example commands, how Pandora maintains inventory, that the skill lives in `skills/trust-intake/`.

- [ ] **Step 2: Generate inventory markdown**

Run: `trust-intake inventory-render`  
Expected: writes `inventory/product-inventory.md`.

- [ ] **Step 3: Run the full unit suite**

Run: `python -m pytest -v`  
Expected: PASS, all tasks’ tests green.

- [ ] **Step 4: Commit**

```bash
git add skills README.md inventory/product-inventory.md
git commit -m "$(cat <<'EOF'
docs: add trust-intake skill and README

EOF
)"
```

---

## Spec coverage

| Spec section | Task |
| --- | --- |
| §3 workflow / approve gate | 8, 9, 10 |
| §4 run folder | 1, 10 |
| §5 layout | 1–12 |
| §6 inventory + match 0.72 | 3, 5 |
| §7 interview | 12 |
| §8 answers schema | 1, 2 |
| §9 CLI including `run` stops at memo | 10 |
| §10 parse | 4 |
| §11 extrapolate | 7 |
| §12 ledger | 6, 9 |
| §13 templates + voice | 8 |
| §14 validate 10 gates | 9 |
| §15 skill contract | 12 |
| §16 errors | 4, 7, 9, 10 |
| §17 tests + golden | 4–11 |
| §18 success criteria | 11, 12 |
| §19 CLI first then skill | task order 1–11 then 12 |

## Self-review notes

- No TBD/TODO in this plan.
- Types are consistent: `validate_answers` / `lint_inventory` return `list[dict]` with `code, path, message`; CLI prints those on stderr.
- `expand_brands` is the only brand normalizer; match and answers both use it.
- Task 4 and Task 8 tell the implementer to write the parser/renderer rather than pasting 200-line bodies here; the tests lock behavior. If an implementer needs a line-by-line parser, follow the test names (`yoy == 0.28` from 100 → 128) as the spec.
