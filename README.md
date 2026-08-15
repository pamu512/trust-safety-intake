# Trust Safety Intake

Trust & Safety feature intake facory  

Two jobs:

1. **Write one document** — interview → workshop memo → BRD / PRD / business case / case study. Numbers must be sourced. Duplicate BRDs are blocked.
2. **Triage a pile** — drop submitted BRDs (Word, PDF, markdown, Confluence HTML). Get unify / deprioritise / high-priority.

The agent only interviews. The CLI does the rest. Do not freehand a BRD.

## Install

Python 3.11+.

```bash
cd ~/Projects/trust-safety-intake
pip install -e ".[dev]"
```

`[dev]` adds pytest. The CLI works with `pip install -e .`.

**Cursor:** this repo ships `[.cursor/rules/trust-intake.mdc](.cursor/rules/trust-intake.mdc)` (always on) and `[.cursor/skills/trust-intake/](.cursor/skills/trust-intake/)`.

**Gemini CLI:** `[.gemini/skills/trust-intake/](.gemini/skills/trust-intake/)` (real files, not a symlink). Enable Skills in `/settings` if needed. Check with `/skills`.

Canonical copy: `[skills/trust-intake/](skills/trust-intake/)`. After editing it, copy into `.cursor/skills/trust-intake/` and `.gemini/skills/trust-intake/`.

## Write one BRD / PRD / business case / case study

```bash
trust-intake init --title "Refund holdout for repeat claimants"
# id is printed. Fill runs/<id>/answers.json (the skill does this by asking one question at a time).

trust-intake parse path/to/numbers.csv --run <id>   # optional
trust-intake run --run <id>                         # match → extrapolate → memo
# read runs/<id>/workshop-memo.md, then the author (not the agent) runs:
trust-intake approve --run <id> --confirm <sha>     # sha is printed by memo
trust-intake render --run <id>
trust-intake validate --run <id>                    # must exit 0
trust-intake decide --run <id>                      # locks the option; updates inventory
```

`run` stops after the memo. `render` refuses unless `APPROVED` contains that memo sha. An empty `APPROVED` file does not count.

Every `€` / `%` in a passing draft must sit on the number ledger (CSV, interview, or a named-method `ESTIMATE`). Missing figures are `ESTIMATE` or `UNKNOWN` — never unlabeled.

A new BRD that overlaps a live control fails unless `answers.json` has a 40-character override. Default is amend, not new.

Worked example (fake euros): `[examples/refund-abuse/](examples/refund-abuse/)`.

## Triage submitted BRDs

Put `.md`, `.docx`, `.pdf`, or `.html` files in a folder:

```bash
trust-intake triage /path/to/brds
```

Writes `triage.md` and `triage.json` in that folder. That is a memo, not a decision. After you accept it:

```bash
trust-intake decide --triage /path/to/brds
```

That locks the labels and updates inventory (unify survivors and high-priority cards; does not add thin / no-numbers / already-ships rows).


| Label             | Meaning                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| **High priority** | € ≥ floor, or 2+ brands/markets — and not deprioritised                                               |
| **Unify**         | Same problem (shared title tokens + overlap ≥ 0.72). Keep one; merge the rest                         |
| **Deprioritise**  | Thin (1 brand + 1 market + € under the floor), already ships, or no numbers. Wins over high-priority. |


Default euro floor is €100k:

```bash
trust-intake triage /path/to/brds --min-euro 100000
```

If extract misses brands or markets, add a sidecar next to the file and re-run:

```json
{
  "brands": ["foodpanda"],
  "markets": ["SG", "HK"],
  "journey": "claims-cancel"
}
```

Name it `Something.meta.json` beside `Something.docx`.

## Inventory (what already ships)

The skill only sees `[inventory/product-inventory.yaml](inventory/product-inventory.yaml)`. That file is the product map: stack, live/planned controls, and docs. `[inventory/markets.yaml](inventory/markets.yaml)` is market codes (SG, DE, TR, …).

```bash
trust-intake inventory-lint
trust-intake inventory-render
```

`inventory/product-inventory.md` is generated. Do not edit it by hand. The agent still asks what already ships.

`decide` writes docs back into the YAML. Jira does not replace that file — it is an optional feed.

### Jira sync (optional)

Mapping: `[inventory/jira.yaml](inventory/jira.yaml)`. Edit that file to match the board. Then:

```bash
trust-intake inventory-sync --from json --file jira-export.json --dry-run
trust-intake inventory-sync --from json --file jira-export.json
trust-intake inventory-sync --from jira --dry-run   # needs JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
```

`--from json` accepts a JQL export (`{ "issues": [ … ] }` or a flat list). `--from jira` calls `/rest/api/2/search` with the `jql` in `jira.yaml`. Descriptions are never imported.

Only rows whose ids start with `doc-jira-` / `ctl-jira-` are upserted. Hand-written controls and `decide` docs stay put. Tickets with no brand and no journey are skipped. A label in `control_labels` (default `capability`) also writes a control.

**Brand labels on the ticket are generic.** Do not put brand names on Jira issues.


| Jira label                       | Stored as    |
| -------------------------------- | ------------ |
| `brand 1` / `brand-1` / `brand1` | first brand  |
| `brand 2` / `brand-2` / `brand2` | second brand |
| `brand 3` / `brand-3` / `brand3` | third brand  |


Keys under `brand_labels` in `jira.yaml` use the same generic names (`brand 1`, `brand-2`, …). Add more aliases there if the board uses different tokens. Journey labels stay as factory names (`account`, `promo`, `claims-cancel`, …) unless you add aliases under `journey_labels`. Status names (`To Do`, `In Progress`, `Done`) map via `status_docs` / `status_controls`.

## Commands

```
trust-intake init --title "..."
trust-intake parse <file.csv|xlsx> --run <id>
trust-intake match --run <id>
trust-intake extrapolate --run <id>
trust-intake memo --run <id>
trust-intake approve --run <id> --confirm <sha>
trust-intake render --run <id>
trust-intake validate --run <id>
trust-intake run --run <id> [--file <csv>]
trust-intake triage <folder> [--min-euro 100000]
trust-intake decide --run <id>
trust-intake decide --triage <folder>
trust-intake inventory-lint
trust-intake inventory-render
trust-intake inventory-sync --from json --file <export.json> [--dry-run]
trust-intake inventory-sync --from jira [--dry-run]
```

Exit codes: `0` ok, `1` gate failure, `2` usage / missing file.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

