# Interview (14 questions)

Ask one question at a time. Prefer the enums. Write answers into `answers.json` as you go. Do not draft a document during the interview.

## Outcome (never skip)

1. What decision must this doc unlock? `ship` | `fund` | `stop` | `change-policy` | `align`
2. What does 90-day success look like? One metric name + direction (`up` | `down` | `hold`) + target if known.
3. Who must say yes? One or more of `finance` | `product` | `eng` | `brand-pnl` | `council` | `other:<name>`

If the original ask does not name a decision, stay here. Suggest a decision and a 90-day metric from what they said. Do not invent a solution yet.

## Current product

4. Which brand(s)? `foodora` | `foodpanda` | `yemeksepeti` | `all` (`all` is stored as the three brands)
5. Which journey? `account` | `promo` | `checkout` | `claims-cancel` | `payout` | `cross-journey`
6. What already ships today for this? Free text, then run `match`.
7. Existing BRD / PRD / ticket / rule? If yes, default `doc_action` to `amend`. Options: `new` | `amend` | `kill`

## Numbers

8. Fill `needed_metrics` (volume, rate, euro_impact, trend, baseline, cx_fp_cost) — value or a file path.
9. If a CSV/XLSX is provided, run `parse`. If not, ask for the smallest table they can share.
10. Any `needed_metrics` slot still empty → run `extrapolate`. Tell the author which figures are estimates before continuing.

## Options and challenge

11. Capture two or three options. One must be `do-nothing`.
12. Devil’s advocate on the favorite: bad-idea test, who loses, unmeasurable in 90 days, why not the live control.
13. Recommendation: one option id + argument against the locked outcome.
14. Chosen doc type: `brd` | `prd` | `business-case` | `case-study`

Then run `memo` and stop. Do not render until the author accepts the memo and `APPROVED` is written.
