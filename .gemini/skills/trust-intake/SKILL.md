---
name: trust-intake
description: Use in Cursor or Gemini CLI when someone at Pandora Trust & Safety wants a BRD, PRD, business case, or case study; when an ask is unclear and an outcome must be locked first; when a request might duplicate an existing control or BRD; when numbers or trends are missing and a CSV/XLSX or extrapolation is needed; or when a PM wants to triage a folder of submitted BRDs.
---

# Trust intake

Read this skill before interviewing. Ask one question at a time.

## Hard rules

- Do not write `draft.md` or a freehand BRD/PRD. If the user asks for a BRD, the first command is `trust-intake init`. Never write BRD markdown yourself.
- Do not skip `init`, `parse`, `match`, `extrapolate`, `memo`, `render`, `validate`, `decide`.
- You are not done until `trust-intake decide` exits 0.
- Do not run `trust-intake approve`. Print the `--confirm` command from `memo`. The author runs it.
- Do not treat inventory as complete; still ask what ships today.
- After locking the outcome, argue for it. Before recommending, attack it.
- Overlap + new BRD → recommend amend. Write new only with override.
- Fill `needed_metrics`. Those values are the ledger. Do not also copy them into `numbers_from_author` unless they are extra named facts.

Questions and enums: [references/interview.md](references/interview.md).  
Named methods and refuse rule: [references/extrapolation.md](references/extrapolation.md).

Write answers into `answers.json` as you go. Do not draft a document during the interview. Do not mkdir run folders — `init` creates `runs/<id>/`.

## Interview order

### 1. Outcome (never skip)

1. What decision must this doc unlock? `ship` | `fund` | `stop` | `change-policy` | `align`
2. What does 90-day success look like? One metric name + direction (`up` | `down` | `hold`) + target if known.
3. Who must say yes? One or more of `finance` | `product` | `eng` | `brand-pnl` | `council` | `other:<name>`

If the original ask does not name a decision, stay here. Suggest a decision and a 90-day metric from what they said. Do not invent a solution yet.

### 2. Current product

4. Which brand(s)? `foodora` | `foodpanda` | `yemeksepeti` | `all` (`all` is stored as the three brands)
5. Which journey? `account` | `promo` | `checkout` | `claims-cancel` | `payout` | `cross-journey`
6. What already ships today for this? Free text, then run `match`.
7. Existing BRD / PRD / ticket / rule? If yes, default `doc_action` to `amend`. Options: `new` | `amend` | `kill`

### 3. Numbers

8. Fill `needed_metrics` (volume, rate, euro_impact, trend, baseline, cx_fp_cost). Rates are fractions (`0.12` for 12%).
9. If a CSV/XLSX is provided, run `parse`. If not, ask for the smallest table they can share.
10. Any `needed_metrics` slot still empty → run `extrapolate`. Tell the author which figures are estimates before continuing.

### 4. Options and challenge

11. Capture two or three options. One must be `do-nothing`.
12. Devil’s advocate on the favorite: bad-idea test, who loses, unmeasurable in 90 days, why not the live control.
13. Recommendation: one option id + argument against the locked outcome.
14. Chosen doc type: `brd` | `prd` | `business-case` | `case-study`

Then run `memo` and stop. Give the author the printed `approve --confirm` command. Do not run it. After they approve: `render`, `validate`, then `decide --run <id>`. For a triage folder, `triage` then wait; the author runs `decide --triage <folder>`.

## CLI

```
trust-intake init --title "..."            # prints run id; writes empty answers.json
trust-intake parse <file> --run <id>
trust-intake match --run <id>
trust-intake extrapolate --run <id>
trust-intake memo --run <id>
trust-intake approve --run <id> --confirm <sha>   # human only; sha is printed by memo
trust-intake render --run <id>
trust-intake validate --run <id>           # memo-stage if no draft; draft-stage if draft.md exists
trust-intake run --run <id> --file <optional.csv>   # parse (if file) → match → extrapolate → memo
trust-intake inventory-lint
trust-intake inventory-render
trust-intake inventory-sync --from json --file <export.json> [--dry-run]
trust-intake inventory-sync --from jira [--dry-run]
trust-intake triage <folder> [--min-euro 100000]
trust-intake decide --run <id>
trust-intake decide --triage <folder>
```

`run` stops after `memo`. It does not render. Render requires `APPROVED`. You are not done until `decide` exits 0. For a folder of submitted BRDs, run `triage` instead of the interview; do not run `decide --triage` (the author does).
