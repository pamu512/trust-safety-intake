# Trust Safety Intake — Design

**Date:** 2026-08-15  
**Repo:** `trust-safety-intake`  
**Status:** Draft for review  
**Audience:** Pandora Trust & Safety (Foodora · Foodpanda · Yemeksepeti). Anyone with an idea — ops, product, market, finance.

## 1. Purpose

A portable GitHub repo Pandora drops into Cursor, Claude, or any agent that reads `SKILL.md`. It turns a fuzzy ask into a decision-ready document.

The agent only interviews. Everything else is a CLI the agent must run and must not skip.

Workshop cannot be skipped. After the workshop memo is approved, the factory writes exactly one of: BRD, PRD, business case, or case study.

The skill argues for the locked outcome. It also attacks that outcome (devil’s advocate) before recommending. It asks about the current product so a duplicate BRD is not created.

## 2. Non-goals

- Not a ticket tracker, Jira sync, or approval workflow beyond a local `APPROVED` file.
- Not a model-training or rules-engine product.
- Does not embed confidential case-pack numbers. Authors supply numbers or a CSV/XLSX.
- Does not freehand a document skeleton. Templates + JSON only.

## 3. Locked workflow

1. **Outcome lock** — If the ask is fuzzy, stop. Ask what decision the doc must unlock, what 90-day success looks like (one metric + direction), who must say yes.
2. **Inventory + interview** — Read inventory. Ask what already ships (brand, journey, live control, existing BRD/PRD/ticket). Overlap → amend/extend, not a new BRD, unless an override reason is written.
3. **Numbers** — Demand volume, rate, € impact, trend, baseline, CX/FP cost. A file goes through `parse`. Missing figures go through `extrapolate` and are labeled `ESTIMATE` (method + range). No unlabeled guesses.
4. **Brainstorm** — Two or three options including “do nothing / use what we already have”.
5. **Devil’s advocate** — Why the favorite fails, who loses, what cannot be measured in 90 days, why not the live control.
6. **Recommend** — One option, argued against the locked outcome. Author approves the workshop memo.
7. **Write** — Only after `APPROVED` exists: render the chosen template.
8. **Validate** — CLI fails the draft if any gate is unmet. Agent fixes and re-validates. No “done” until validate exits 0.

## 4. Architecture

```
Author (any Pandora function)
        │  conversation
        ▼
Agent (SKILL.md) ── writes answers.json, option prose, recommendation prose
        │  must shell out
        ▼
trust-intake CLI
        │
        ├─ init         create runs/<id>/ + empty answers.json
        ├─ parse        CSV/XLSX → facts.json
        ├─ match        answers + inventory → overlaps.json
        ├─ extrapolate  facts + answers → estimates.json
        ├─ memo         JSON → workshop-memo.md
        ├─ approve      write APPROVED (only after the author says yes)
        ├─ render       memo + JSON → draft.md
        └─ validate     run folder → validation.json (memo-stage or draft-stage)
```

Each intake is a run folder:

```
runs/<id>/
  answers.json
  facts.json
  overlaps.json
  estimates.json
  workshop-memo.md
  APPROVED                 # created only after the author says the memo is accepted
  draft.md
  validation.json
```

`<id>` is `YYYYMMDD-HHMMSS-<slug>` from the outcome title, created by `trust-intake init --title "..."`. The agent does not mkdir run folders or invent parallel paths.

## 5. Repository layout

```
trust-safety-intake/
  README.md
  pyproject.toml
  skills/trust-intake/SKILL.md
  skills/trust-intake/references/interview.md
  skills/trust-intake/references/extrapolation.md
  inventory/product-inventory.yaml      # source of truth
  inventory/product-inventory.md        # generated; do not edit by hand
  templates/workshop-memo.md
  templates/brd.md
  templates/prd.md
  templates/business-case.md
  templates/case-study.md
  src/trust_intake/
    __init__.py
    cli.py
    parse_table.py
    match_inventory.py
    extrapolate.py
    render.py
    validate_draft.py
    inventory_lint.py
    ledger.py
  tests/
  examples/refund-abuse/                # anonymized golden run
  docs/superpowers/specs/
```

Python package name: `trust-intake` (CLI) / `trust_intake` (import).  
Dependencies: Python 3.11+, PyYAML, openpyxl. Nothing else. Fuzzy overlap uses stdlib `difflib`.

## 6. Inventory (anti-duplicate source of truth)

`inventory/product-inventory.yaml` is the only file humans edit.

Required top-level keys:

- `brands` — `foodora`, `foodpanda`, `yemeksepeti`
- `journeys` — `account`, `promo`, `checkout`, `claims-cancel`, `payout`, `cross-journey`
- `stack` — list of `{id, name, layer, notes}`
- `controls` — list of `{id, name, type, journey, brands[], status, owner, related_docs[]}`
  - `type`: `rule` | `ml` | `policy` | `ops`
  - `status`: `live` | `pilot` | `planned` | `retired`
- `docs` — list of `{id, type, title, status, journey, brands[], link}`
  - `type`: `brd` | `prd` | `business-case` | `case-study` | `ticket`
  - `status`: `draft` | `open` | `approved` | `shipped` | `killed`

`trust-intake inventory-render` regenerates the markdown view. `trust-intake inventory-lint` fails on missing ids, unknown enums, dangling `related_docs`, or duplicate ids.

Seed at ship: brands, journeys, and stack placeholders (rules engine, ML risk score, SQL warehouse, Looker, manual investigations). Controls and docs start empty except for one anonymized example row. No confidential pack figures.

Match rules (`match`):

- Compare author `title` + `journey` + `brands` to `controls` and `docs`.
- Score = weighted: journey exact (0.4) + brand overlap (0.3) + `difflib` title ratio (0.3).
- `score >= 0.72` is an overlap.
- If the author chose `new` and any overlap exists, validate fails unless `answers.duplicate_override` is a non-empty reason string (min 40 characters).
- Default recommendation in the memo is `amend` when overlap exists.

The agent still asks “what already ships?” after reading inventory. Files are not a substitute for the interview.

## 7. Interview (agent-only)

Ask one question at a time. Prefer the multiple-choice options below. Write answers into `answers.json` as you go. Do not draft a document during the interview.

### 7.1 Outcome (never skip)

1. What decision must this doc unlock? `ship` | `fund` | `stop` | `change-policy` | `align`
2. What does 90-day success look like? One metric name + direction (`up` | `down` | `hold`) + target if known.
3. Who must say yes? One or more of `finance` | `product` | `eng` | `brand-pnl` | `council` | `other:<name>`

If the original ask does not name a decision, stay here. Suggest a decision and a 90-day metric from what they said. Do not invent a solution yet.

### 7.2 Current product

4. Which brand(s)? `foodora` | `foodpanda` | `yemeksepeti` | `all` (`all` is stored as the three brands)
5. Which journey? `account` | `promo` | `checkout` | `claims-cancel` | `payout` | `cross-journey`
6. What already ships today for this? Free text, then run `match`.
7. Existing BRD / PRD / ticket / rule? If yes, default `doc_action` to `amend`. Options: `new` | `amend` | `kill`

### 7.3 Numbers

8. Fill `needed_metrics` (volume, rate, euro_impact, trend, baseline, cx_fp_cost) — value or a file path.
9. If a CSV/XLSX is provided, run `parse`. If not, ask for the smallest table they can share.
10. Any `needed_metrics` slot still empty → run `extrapolate`. Tell the author which figures are estimates before continuing.

### 7.4 Options and challenge

11. Capture two or three options. One must be `do-nothing`.
12. Devil’s advocate on the favorite: bad-idea test, who loses, unmeasurable in 90 days, why not the live control.
13. Recommendation: one option id + argument against the locked outcome.
14. Chosen doc type: `brd` | `prd` | `business-case` | `case-study`

Then run `memo` and stop. Do not render until the author accepts the memo and `APPROVED` is written.

## 8. `answers.json` schema

Required keys. Extra keys are allowed; missing required keys fail `memo` and `validate`.

```yaml
run_id: string
title: string
decision: ship | fund | stop | change-policy | align
success:
  metric: string
  direction: up | down | hold
  target: string | null
approvers: [string]
brands: [foodora | foodpanda | yemeksepeti]
journey: account | promo | checkout | claims-cancel | payout | cross-journey
already_ships: string
doc_action: new | amend | kill
amend_target_id: string | null
duplicate_override: string | null
elapsed_fraction: number | null          # 0–1; required for run-rate
shares: {string: number}                 # child → 0–1; required for share-of-parent
doc_type: brd | prd | business-case | case-study
needed_metrics:
  volume: {value: number | null, unit: string | null}
  rate: {value: number | null, unit: string | null}
  euro_impact: {value: number | null, unit: string | null}
  trend: {value: number | null, unit: string | null}
  baseline: {value: number | null, unit: string | null}
  cx_fp_cost: {value: number | null, unit: string | null}
numbers_from_author:
  - name: string
    value: number
    unit: string
    source: interview
options:
  - id: string
    title: string
    summary: string
    is_do_nothing: bool
favorite_option_id: string
devils_advocate:
  why_fails: string
  who_loses: string
  cannot_measure: string
  why_not_live_control: string
recommendation:
  option_id: string
  argument: string
```

Prose fields (`already_ships`, option summaries, devil’s advocate, recommendation.argument) are written by the agent. Minimum 40 characters each. The CLI does not generate that prose.

`favorite_option_id` is the option the devil’s advocate attacks. `recommendation.option_id` may differ (the challenge can change the pick). Both must be ids in `options`.

`needed_metrics` values the author typed also appear in `numbers_from_author` (same name as the slot). Null slots are the extrapolate gaps.

## 9. CLI

```
trust-intake init --title "..."            # prints run id; writes empty answers.json
trust-intake parse <file> --run <id>
trust-intake match --run <id>
trust-intake extrapolate --run <id>
trust-intake memo --run <id>
trust-intake approve --run <id>            # writes APPROVED; only after the author says yes
trust-intake render --run <id>
trust-intake validate --run <id>           # memo-stage if no draft; draft-stage if draft.md exists
trust-intake run --run <id> --file <optional.csv>   # parse (if file) → match → extrapolate → memo
trust-intake inventory-lint
trust-intake inventory-render
```

`run` stops after `memo`. It does not render. Render requires `APPROVED`.

Exit codes: `0` ok, `1` validation/gate failure, `2` usage/IO error. Failures print a machine-readable reason list to stderr and write `validation.json` when applicable.

## 10. Parse

Input: `.csv` or `.xlsx`. XLSX: every sheet becomes a named table.

Behavior:

- Infer column types: date, number, category, text.
- If a date column exists, compute period-over-period and YoY when two or more comparable periods exist.
- If a brand or market column exists, emit splits.
- Emit totals, null rates, and a `warnings[]` list (empty sheets, single-row tables, non-numeric “€” columns that failed to parse).
- Write `facts.json`:

```yaml
tables:
  - name: string
    columns: [{name, type}]
    row_count: int
    totals: {column: number}
    missingness: {column: float}   # 0–1
    series:                        # only if date column
      - period: string
        values: {column: number}
    splits:                        # only if brand/market column
      - key: string
        values: {column: number}
    warnings: [string]
derived:
  - name: string
    value: number
    unit: string | null
    source: csv
    method: sum | yoy | pop | split-share
```

No extrapolation inside `parse`. Parse only reports what is in the file.

## 11. Extrapolate

Runs only for `needed_metrics` slots that are still null after `facts.derived` and `numbers_from_author` are applied. Inputs to a method must already be on the ledger (csv or interview). Inventory is not a numeric source.

Allowed methods — no others:

| Method | When | How | Range |
| --- | --- | --- | --- |
| `run-rate` | A partial-period value and `elapsed_fraction` (0–1) exist on the ledger or in `answers.elapsed_fraction` | `(value / elapsed_fraction) * 1.0` | ±20% |
| `share-of-parent` | Child missing; parent value and a share (0–1) exist on the ledger or in `answers.shares.<child>` | `parent * share` | ±25% |
| `last-period-carry` | `facts.tables[].series` has a latest period for that measure | copy last period | ±30% |
| `peer-brand-ratio` | Peer brand measure and both brands’ GMV exist on the ledger | `peer * (target_gmv / peer_gmv)` | ±35% |

Refuse (do not invent) when no allowed method applies. The memo lists refused fields as `UNKNOWN — author must supply`.

Every estimate:

```yaml
name: string
value: number
unit: string
source: ESTIMATE
method: run-rate | share-of-parent | last-period-carry | peer-brand-ratio
inputs: [string]          # fact or answer names used
range: {low: number, high: number}
```

The skill must tell the author which figures are estimates before asking them to approve the memo.

## 12. Number ledger

`ledger.py` unions:

- `facts.derived[]` (`source: csv`)
- `answers.numbers_from_author[]` (`source: interview`)
- `estimates[]` (`source: ESTIMATE`)

Scan memo/draft for quantity tokens only:

- `€` / `EUR` amounts (`€1.2M`, `EUR 400k`)
- percents (`39%`, `1.28%`)
- a number immediately followed by a unit from this allowlist: `orders`, `GMV`, `bps`, `FTE`, `flags`, `claims`, `payouts`

Ignore dates, `90-day`, section numbers, and the 40-character rule text. Each matched token must equal a ledger `value` (formatting allowed: `1.2M` = `1200000`). Unresolved tokens fail validate.

Rendering inserts numbers only via `{{ledger.name}}` placeholders. Agents must not paste raw figures into template holes.

Inventory may be cited in the assumptions table as `source: inventory` for non-numeric claims only. A number that originated in inventory must be copied into `numbers_from_author` before it may appear in a doc.

## 13. Templates and voice

Shared rules for every template:

- Opening: locked outcome, 90-day success, approvers.
- Assumptions table. Each row: claim, source (`csv` | `interview` | `ESTIMATE` | `inventory`), validate-if-unsigned. `inventory` is allowed only when the claim has no quantity token.
- Options table including do-nothing.
- Devil’s advocate section (the four fields, not a paragraph that can be skipped).
- Recommendation argued against the locked outcome.
- Number placeholders are `{{ledger.*}}` only.
- Voice: direct, no unlabeled guesses, Finance-grade. “Validate” on any figure not Finance-signed. Same posture as the Pandora Fraud LOB brief: working ambition is not a vow.

Doc-specific body (after the shared head):

| Type | Extra sections | Handed to |
| --- | --- | --- |
| BRD | Problem, business requirements (testable), metrics, non-goals, amend-target if `doc_action=amend` | Product / Eng |
| PRD | Solution, journeys, in-scope / out-of-scope, acceptance criteria, non-goals | Eng |
| Business case | Cost, impact, options comparison, ask (fund/stop/ship) | Finance / leadership |
| Case study | Before → intervention → after, numbered claims | Alignment / narrative |

`render` fills the template from JSON. Empty required prose fields fail render. The agent may edit prose fields in `answers.json` and re-render. It may not rewrite `draft.md` by hand to sneak around the ledger.

## 14. Validate (hard fail)

`validate` exits 1 if any of these are true:

1. `answers.json` missing a required key or a prose field < 40 characters.
2. No option with `is_do_nothing: true`.
3. `devils_advocate` any field empty.
4. `doc_action=new` and overlaps exist and `duplicate_override` is missing or < 40 characters.
5. `workshop-memo.md` missing.
6. A quantity token in memo (and draft, if present) is not on the ledger.
7. An `ESTIMATE` row lacks `method`, `inputs`, or `range`.
8. Draft-stage only: `draft.md` exists without `APPROVED`, or the chosen `doc_type` headings are missing.
9. Inventory lint would fail (stale/broken inventory).
10. `favorite_option_id` or `recommendation.option_id` is not in `options`.

Memo-stage = no `draft.md` yet. Draft-stage = `draft.md` exists. `validate` picks the stage automatically.

`validation.json` lists each failure as `{code, path, message}`. The skill fixes `answers.json` or the data files, re-runs the failed step, and validates again.

## 15. Skill contract

`SKILL.md` description (trigger only, no workflow summary):

> Use when someone at Pandora Trust & Safety wants a BRD, PRD, business case, or case study; when an ask is unclear and an outcome must be locked first; when a request might duplicate an existing control or BRD; or when numbers/trends are missing and a CSV/XLSX or extrapolation is needed.

Hard rules in the skill body:

- Read this skill before interviewing.
- One question at a time.
- Do not write `draft.md` or a freehand BRD/PRD.
- Do not skip `parse`, `match`, `extrapolate`, `memo`, `approve`, `render`, `validate`.
- Do not treat inventory as complete; still ask what ships today.
- After locking the outcome, argue for it. Before recommending, attack it.
- If asked for both a new BRD and an overlapping live control, recommend amend. Write new only with override.

## 16. Error handling

| Situation | Behavior |
| --- | --- |
| Fuzzy ask | Stay in outcome lock. Propose a decision + metric. No memo. |
| No inventory file | `inventory-lint` exits 2. Tell the author to add `inventory/product-inventory.yaml`. |
| Unreadable CSV/XLSX | `parse` exits 2 with the sheet/column error. Continue interview with `numbers_from_author` or stop if they have nothing. |
| Extrapolate cannot apply a method | Field is `UNKNOWN`. Memo can be written; render of a doc that requires that field fails until supplied. |
| Author wants new BRD on overlap, no override | `match`/`validate` fail. Do not approve or render. |
| Author edits `draft.md` by hand | Next `validate` still ledger-checks. Re-render overwrites `draft.md` from JSON. |
| Missing `APPROVED` | `render` exits 1. |

## 17. Testing (ships with the repo)

- `parse`: CSV with dates → YoY present; XLSX multi-sheet; empty sheet → warning; euro-like text that fails to parse → warning not a crash.
- `match`: same journey+brand+similar title → overlap ≥ 0.72; different journey → no overlap; override < 40 chars → validate fail.
- `extrapolate`: run-rate from a half-year; refuse when no parent/peer/period exists.
- `ledger`: draft with an extra `€12M` not in JSON → validate fail.
- `validate`: golden `examples/refund-abuse` exits 0; a fixture missing devil’s advocate exits 1; a fixture with unlabeled number exits 1.
- `render`: each of the four templates produces the required headings from the golden answers.
- `inventory-lint`: duplicate id fails; dangling `related_docs` fails.

The refund-abuse example is anonymized (fake brand codes, fake euros). It is the runnable check that the factory works.

## 18. Success criteria

The repo is done when all of the following are true:

1. A stranger at Pandora can clone, `pip install -e .`, and run the golden example to exit 0.
2. An agent following `SKILL.md` cannot produce a draft without a workshop memo and `APPROVED`.
3. A new-BRD request that matches a live control fails without a written override.
4. Every number in a passing draft is on the ledger with a source tag.
5. Missing numbers are either `ESTIMATE` (allowed method) or `UNKNOWN`, never unlabeled.

## 19. Implementation order

Build the CLI and its tests (including the golden example) first. Then `SKILL.md`. The skill is instructions around a factory that already fails closed.
