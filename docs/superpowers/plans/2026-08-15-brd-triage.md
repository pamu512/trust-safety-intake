# BRD Portfolio Triage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `trust-intake triage <folder>` so a PM can drop mixed BRDs and get unify / deprioritise / high-priority labels with hard reasons.

**Architecture:** New modules extract text → card → cluster/label → memo. Reuse `score_overlap`, `scan_quantities`, `match`, inventory lint. CLI gains one subcommand. No agent ranking.

**Tech Stack:** Existing package plus `python-docx` and `pypdf`. Stdlib `html.parser` for Confluence HTML.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-15-brd-triage-design.md`.
- Default `--min-euro` is `100000`.
- Unify threshold `>= 0.72`. Known journeys: `0.4` journey + `0.3` brand + `0.3` title. Either journey `unknown`: `0.5` brand + `0.5` title.
- Deprioritise reasons: `thin` (1 brand AND 1 market AND euro missing or `< min-euro`), `already-ships` (inventory overlap `>= 0.72`), `no-numbers` (no euro, volume, or rate).
- High-priority: `len(brands) >= 2` OR `len(markets) >= 2`.
- Do not invent brands/markets/euros. Empty extract → `extraction-gap`.
- Sidecar `<stem>.meta.json` overrides brands/markets/journey/euro_impact/volume/rate.
- New deps only: `python-docx`, `pypdf`.
- Exit `0` if ≥1 card scored; `1` if folder has no readable BRDs; `2` missing folder / IO.
- Unsupported suffix → warning, do not crash.
- Reuse `score_overlap` / `match` / `scan_quantities`. Do not copy inventory pack numbers.

## File map

| File | Responsibility |
| --- | --- |
| `inventory/markets.yaml` | Market ids + aliases |
| `src/trust_intake/markets.py` | Load + lint + alias resolve |
| `src/trust_intake/triage_read.py` | File → text (+ sidecar) |
| `src/trust_intake/triage_extract.py` | Text → card fields |
| `src/trust_intake/triage.py` | Cluster, labels, json/md |
| `src/trust_intake/cli.py` | `triage` subcommand |
| `pyproject.toml` | Add deps |
| `tests/test_triage.py` | All triage tests |
| `tests/fixtures/triage/` | Tiny md/html/docx/pdf samples |

---

### Task 1: Markets file + lint

**Files:**
- Create: `inventory/markets.yaml`
- Create: `src/trust_intake/markets.py`
- Modify: `src/trust_intake/inventory_lint.py` — `lint_markets` can live in `markets.py`; `inventory-lint` CLI later calls both. This task only adds `markets.py` + tests.
- Test: `tests/test_markets.py`

**Interfaces:**
- Consumes: PyYAML
- Produces: `load_markets(path: Path) -> dict[str, list[str]]` mapping `id → aliases including id`; `lint_markets(data: dict) -> list[dict]`; `resolve_markets(text: str, markets: dict[str, list[str]]) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_markets.py
from pathlib import Path

from trust_intake.markets import lint_markets, load_markets, resolve_markets


def test_seed_lints_clean():
    data = load_markets(Path("inventory/markets.yaml"))
    assert lint_markets({"markets": [{"id": k, "aliases": v} for k, v in _as_rows(data)]}) == [] or True
    # load_markets returns id→aliases; lint the raw yaml shape:
    import yaml
    raw = yaml.safe_load(Path("inventory/markets.yaml").read_text())
    assert lint_markets(raw) == []


def test_lint_duplicate_id():
    fails = lint_markets({"markets": [{"id": "SG", "aliases": []}, {"id": "SG", "aliases": []}]})
    assert any(f["code"] == "duplicate_id" for f in fails)


def test_singapore_alias():
    markets = {"SG": ["SG", "Singapore"], "DE": ["DE", "Germany"]}
    assert resolve_markets("Launch in Singapore and DE", markets) == ["DE", "SG"]
```

Fix `test_seed_lints_clean` to only use the yaml.safe_load path (delete the `or True` line).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_markets.py -v`  
Expected: FAIL import error.

- [ ] **Step 3: Write implementation**

`inventory/markets.yaml` seed ids: `DE AT NL SE NO FI DK SG HK MY TH TW PH PK BD TR` with obvious English aliases (Germany, Austria, Netherlands, Sweden, Norway, Finland, Denmark, Singapore, Hong Kong, Malaysia, Thailand, Taiwan, Philippines, Pakistan, Bangladesh, Turkey) plus local names where obvious (Deutschland, Türkiye).

`markets.py`:

```python
from __future__ import annotations
from pathlib import Path
import re
import yaml

def load_markets(path: Path) -> dict[str, list[str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    fails = lint_markets(raw if isinstance(raw, dict) else {})
    if fails:
        raise ValueError(fails)
    out: dict[str, list[str]] = {}
    for row in raw["markets"]:
        aliases = [row["id"], *(row.get("aliases") or [])]
        out[row["id"]] = aliases
    return out

def lint_markets(data: dict) -> list[dict]:
    fails = []
    if "markets" not in data:
        return [{"code": "missing_key", "path": "markets", "message": "missing markets"}]
    seen = set()
    for i, row in enumerate(data["markets"] or []):
        rid = (row or {}).get("id")
        if not rid:
            fails.append({"code": "missing_id", "path": f"markets[{i}]", "message": "id required"})
            continue
        if rid in seen:
            fails.append({"code": "duplicate_id", "path": f"markets[{i}]", "message": rid})
        seen.add(rid)
    return fails

def resolve_markets(text: str, markets: dict[str, list[str]]) -> list[str]:
    found = set()
    for mid, aliases in markets.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.I):
                found.add(mid)
                break
    return sorted(found)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_markets.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add inventory/markets.yaml src/trust_intake/markets.py tests/test_markets.py
git commit -m "$(cat <<'EOF'
feat: add markets allowlist for BRD triage

EOF
)"
```

---

### Task 2: Read files + extract cards

**Files:**
- Create: `src/trust_intake/triage_read.py`
- Create: `src/trust_intake/triage_extract.py`
- Modify: `pyproject.toml` — add `python-docx>=1.1`, `pypdf>=5.0`
- Test: `tests/test_triage_extract.py`
- Create: `tests/fixtures/triage/repeat-claimant.md`

**Interfaces:**
- Produces: `read_document(path: Path) -> str`; `read_sidecar(path: Path) -> dict`; `extract_card(path: Path, text: str, sidecar: dict, markets: dict) -> dict` (card without labels/cluster)

Brand rules: word-boundary `foodora|foodpanda|yemeksepeti`; `all brands` / `all three brands` → all three.

Journey: tokens `account`, `promo`, `checkout`, `claims-cancel` / `claims`+`cancel`, `payout`, `cross-journey`. One hit → that journey; several → `cross-journey`; none → `unknown`.

Quantities: `scan_quantities`. First token containing `€` or `EUR` → euro_impact. First token containing `%` → rate. First token containing `orders|claims|flags|payouts` → volume.

Title: first line matching `^#\s+` or first non-empty line, else stem.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_triage_extract.py
from pathlib import Path
from trust_intake.triage_extract import extract_card
from trust_intake.triage_read import read_document

FIXTURE = Path("tests/fixtures/triage/repeat-claimant.md")

def test_md_extracts_brands_markets_euro(tmp_path, monkeypatch):
    text = FIXTURE.read_text()
    markets = {"SG": ["SG", "Singapore"], "HK": ["HK", "Hong Kong"]}
    card = extract_card(FIXTURE, text, {}, markets)
    assert card["brands"] == ["foodpanda"]
    assert card["markets"] == ["HK", "SG"]
    assert card["euro_impact"]["value"] == 2_500_000
    assert card["journey"] in {"claims-cancel", "unknown"}

def test_all_three_brands():
    markets = {}
    card = extract_card(Path("x.md"), "# X\nall three brands\n", {}, markets)
    assert card["brands"] == ["foodora", "foodpanda", "yemeksepeti"]

def test_sidecar_overrides_brands():
    card = extract_card(Path("x.md"), "# X\nfoodora\n", {"brands": ["foodpanda"]}, {})
    assert card["brands"] == ["foodpanda"]
```

`tests/fixtures/triage/repeat-claimant.md`:

```markdown
# Repeat claimant static control

Foodpanda Singapore and Hong Kong. Exposure €2.5M. claims-cancel journey.
10000 claims at 12%.
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/bin/python -m pytest tests/test_triage_extract.py -v`  
Expected: FAIL import.

- [ ] **Step 3: Implement readers + extract**

`triage_read.py`: `.md/.txt` read_text; `.html/.htm` `html.parser` strip tags; `.docx` python-docx paragraphs; `.pdf` pypdf page extract_text. Else raise `ValueError("unsupported")`. Sidecar: `path.with_suffix(path.suffix + ".meta.json")` is wrong — sidecar is `<stem>.meta.json` e.g. `repeat-claimant.meta.json` = `path.with_name(path.stem + ".meta.json")`.

`triage_extract.py` implements the rules above. `euro_impact` source `sidecar` if sidecar has it, else `extract` or `missing`.

Also add a tiny docx/pdf write in tests using python-docx and pypdf (or reportlab-free: pypdf can write a simple page via a pre-checked-in binary fixture). Prefer generating docx in the test with `Document()`. For PDF, generate with pypdf `PageObject` is painful — check in a 1-page fixture PDF created once in the test via a minimal writer, or skip PDF in this task and add in Task 4 CLI golden. **This task: md + html string + docx generated in test. PDF fixture in Task 4.**

HTML test: `extract_card` on `read_document` of a temp `.html` with `<h1>Title</h1><p>foodora Germany</p>`.

- [ ] **Step 4: Tests pass**

Run: `.venv/bin/pip install -e ".[dev]" && .venv/bin/python -m pytest tests/test_triage_extract.py tests/test_markets.py -v`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/trust_intake/triage_read.py src/trust_intake/triage_extract.py tests/test_triage_extract.py tests/fixtures/triage
git commit -m "$(cat <<'EOF'
feat: extract BRD cards from mixed documents

EOF
)"
```

---

### Task 3: Cluster, labels, memo

**Files:**
- Create: `src/trust_intake/triage.py`
- Test: `tests/test_triage.py`

**Interfaces:**
- Consumes: `score_overlap`, `match`, `extract_card`, `load_markets`, `load_inventory`
- Produces: `score_pair(a: dict, b: dict) -> float`; `label_cards(cards: list[dict], inventory: dict, min_euro: float) -> list[dict]`; `cluster_unify(cards: list[dict]) -> list[dict]` (mutates cluster_id + unify label); `render_triage_md(payload: dict) -> str`; `run_triage(folder: Path, inventory: dict, markets: dict, min_euro: float) -> tuple[int, dict]`

`score_pair`: if both journeys known and not unknown, call `score_overlap(a["title"], a["journey"], a["brands"], {"title": b["title"], "journey": b["journey"], "brands": b["brands"]})`. Else `0.5 * brand_jaccard + 0.5 * difflib.SequenceMatcher(None, a["title"].lower(), b["title"].lower()).ratio()`.

Union-find / BFS for connected components at `>= 0.72`.

Survivor: max `euro_impact.value or -1`, then max `len(brands)+len(markets)`.

`run_triage` walks folder (non-recursive), skips `triage.json` / `triage.md` / `*.meta.json`, unsupported → `warnings`.

- [ ] **Step 1: Failing tests** (in `tests/test_triage.py`)

```python
def test_similar_titles_unify():
    # two cards same journey+brand, similar title → one cluster

def test_thin_single_brand_market_low_euro():
    # 1 brand, 1 market, 50_000, min_euro 100000 → thin

def test_two_brands_no_numbers_high_priority_and_no_numbers():
    ...

def test_already_ships_seed_control():
    # title/journey/brands matching Repeat claimant / claims-cancel / foodpanda
    # against seed inventory → already-ships

def test_xlsx_warning_not_crash(tmp_path):
    (tmp_path / "x.xlsx").write_bytes(b"not-a-real-xlsx")
    (tmp_path / "ok.md").write_text("# A\nfoodora Singapore\n€2M\n")
    code, payload = run_triage(tmp_path, inv, markets, 100000)
    assert code == 0
    assert payload["warnings"]
```

Use real `load_inventory(Path("inventory/product-inventory.yaml"))` and `load_markets(Path("inventory/markets.yaml"))`.

- [ ] **Step 2: Fail** — import error.

- [ ] **Step 3: Implement `triage.py`** including markdown sections: High priority, Unify, Deprioritise, Extraction gaps, Warnings. JSON keys: `cards`, `clusters`, `warnings`, `min_euro`.

- [ ] **Step 4: Pass** — `.venv/bin/python -m pytest tests/test_triage.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/triage.py tests/test_triage.py
git commit -m "$(cat <<'EOF'
feat: cluster and label submitted BRDs

EOF
)"
```

---

### Task 4: CLI + PDF fixture + inventory-lint markets

**Files:**
- Modify: `src/trust_intake/cli.py` — add `triage` subcommand and `--min-euro`; `inventory-lint` also lints `inventory/markets.yaml` when present (add `--markets` default).
- Modify: `src/trust_intake/inventory_lint.py` only if you choose to call `lint_markets` from CLI, not by changing product-inventory schema.
- Test: `tests/test_cli.py` — add `test_triage_empty_folder_exits_1`, `test_triage_scores_md`
- Create: `tests/fixtures/triage/sample.pdf` generated in test or a checked-in one-pager
- Modify: `README.md` — one paragraph + command
- Modify: `skills/trust-intake/SKILL.md` — one trigger line only if you add “when a PM wants to triage a folder of submitted BRDs” to the description. Spec said CLI-only; **do not change the skill unless a one-line WHEN clause is needed for discovery.** Add the WHEN clause to the description (trigger only, no workflow).

**Interfaces:**
- `main(["triage", str(folder), "--min-euro", "100000"])` writes `triage.json` and `triage.md`

- [ ] **Step 1: Failing CLI tests**

```python
def test_triage_empty_folder_exits_1(tmp_path):
    assert main(["triage", str(tmp_path)]) == 1

def test_triage_missing_folder_exits_2(tmp_path):
    assert main(["triage", str(tmp_path / "nope")]) == 2

def test_triage_writes_memo(tmp_path):
    (tmp_path / "a.md").write_text("# Repeat claimant static control\nfoodpanda Singapore\n€2.5M\nclaims-cancel\n")
    (tmp_path / "b.md").write_text("# Repeat claimant static rule\nfoodpanda Hong Kong\n€1M\nclaims-cancel\n")
    assert main(["triage", str(tmp_path)]) == 0
    assert (tmp_path / "triage.md").is_file()
    md = (tmp_path / "triage.md").read_text()
    assert "High priority" in md or "Unify" in md or "Deprioritise" in md
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Wire CLI**

```python
triage_p = sub.add_parser("triage", parents=[parent])
triage_p.add_argument("folder")
triage_p.add_argument("--min-euro", type=float, default=100000)
triage_p.add_argument("--markets", default="inventory/markets.yaml")
```

`_cmd_triage`: missing folder → 2; `run_triage`; write json + md; return code.

PDF: add `test_read_pdf` that writes a one-page PDF using pypdf if easy; else a committed tiny PDF in `tests/fixtures/triage/hello.pdf`. Must extract the word `foodora`.

- [ ] **Step 4: Full suite**

Run: `.venv/bin/python -m pytest -v`  
Expected: all existing + new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/trust_intake/cli.py tests/test_cli.py README.md skills/trust-intake/SKILL.md tests/fixtures/triage
git commit -m "$(cat <<'EOF'
feat: add trust-intake triage command

EOF
)"
```

---

## Spec coverage

| Spec | Task |
| --- | --- |
| markets.yaml + lint | 1 |
| readers md/html/docx/pdf | 2, 4 |
| extract + sidecar | 2 |
| unify / thin / already-ships / no-numbers / high-priority | 3 |
| triage.json + triage.md | 3, 4 |
| CLI exit codes + warnings | 4 |
| Tests listed in spec §11 | 2–4 |
