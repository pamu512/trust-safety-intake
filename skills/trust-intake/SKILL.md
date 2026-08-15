---
name: trust-intake
description: Use when someone at Pandora Trust & Safety wants a BRD, PRD, business case, or case study; when an ask is unclear and an outcome must be locked first; when a request might duplicate an existing control or BRD; or when numbers or trends are missing and a CSV/XLSX or extrapolation is needed.
---

# Trust intake

Read this skill before interviewing. Ask one question at a time.

## Hard rules

- Do not write `draft.md` or a freehand BRD/PRD.
- Do not skip `init`, `parse`, `match`, `extrapolate`, `memo`, `approve`, `render`, `validate`.
- Do not treat inventory as complete; still ask what ships today.
- After locking the outcome, argue for it. Before recommending, attack it.
- Overlap + new BRD → recommend amend. Write new only with override.

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

8. Fill `needed_metrics` (volume, rate, euro_impact, trend, baseline, cx_fp_cost) — value or a file path.
9. If a CSV/XLSX is provided, run `parse`. If not, ask for the smallest table they can share.
10. Any `needed_metrics` slot still empty → run `extrapolate`. Tell the author which figures are estimates before continuing.

### 4. Options and challenge

11. Capture two or three options. One must be `do-nothing`.
12. Devil’s advocate on the favorite: bad-idea test, who loses, unmeasurable in 90 days, why not the live control.
13. Recommendation: one option id + argument against the locked outcome.
14. Chosen doc type: `brd` | `prd` | `business-case` | `case-study`

Then run `memo` and stop. Do not render until the author accepts the memo and `APPROVED` is written.

## CLI

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
