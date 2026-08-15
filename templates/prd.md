# {{answers.title}}

## Locked outcome
- Decision: {{answers.decision}}
- Document action: {{answers.doc_action}} (amend target: {{answers.amend_target_id}})
- Brands: {{answers.brands}}
- Journey: {{answers.journey}}
- 90-day success: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}
- Approvers who must say yes: {{answers.approvers}}

## Executive summary
This PRD asks {{answers.approvers}} to {{answers.decision}} **{{favorite.title}}** on {{answers.brands}} / {{answers.journey}}.

{{answers.recommendation.argument}}

Current product: {{answers.already_ships}}

90-day success is {{answers.success.metric}} {{answers.success.direction}} ({{answers.success.target}}). Volume in scope: {{ledger.volume}}.

## Solution
{{answers.recommendation.argument}}

**{{favorite.title}}** (`{{answers.recommendation.option_id}}`): {{favorite.summary}}

This is a {{answers.doc_action}} on {{answers.journey}} for {{answers.brands}}. Engineering builds only this option. Do-nothing stays available if the 90-day metric cannot be instrumented.

## Journeys
Primary journey: **{{answers.journey}}**.

- In this PRD, change behavior only on {{answers.journey}} for {{answers.brands}}.
- Do not widen to another journey without a new decide.
- If `doc_action` is amend, the change lands on `{{answers.amend_target_id}}`, not a parallel surface.

## Current product
What already ships (author): {{answers.already_ships}}

Inventory overlaps at or above the match threshold:

{{#each overlap_rows}}
- {{kind}} `{{id}}`: {{title}} (score {{score}})
{{/each}}

If the list above is empty, match found no live control or existing doc at threshold. Still treat the author text as the source for what ships — inventory is not complete.

## In scope
{{answers.already_ships}}

- Implement **{{favorite.title}}** on {{answers.brands}} {{answers.journey}}: {{favorite.summary}}
- Instrument {{answers.success.metric}} so {{answers.approvers}} can see {{answers.success.direction}} toward {{answers.success.target}} in 90 days.
- Operate on ledger volume {{ledger.volume}}. Do not invent a second volume.
- Keep a runnable do-nothing path.

## Out of scope
- Journeys other than {{answers.journey}}.
- Brands other than {{answers.brands}}.
- Rebuild of live controls unless `doc_action` is new with a written override.
- Amend target `{{answers.amend_target_id}}` is out of scope unless `doc_action` is amend.
- Unlabeled euro or rate guesses.

## Acceptance criteria
These must be testable in 90 days.

- **AC1 — Option.** {{favorite.title}} is live on {{answers.brands}} {{answers.journey}} as described: {{favorite.summary}}
- **AC2 — Metric.** {{answers.success.metric}} is reported {{answers.success.direction}} against {{answers.success.target}}. {{answers.approvers}} can sign it.
- **AC3 — Volume.** Measured population matches ledger volume {{ledger.volume}}.
- **AC4 — Action type.** `doc_action` is {{answers.doc_action}}. Amend extends `{{answers.amend_target_id}}`. New does not silently replace a live control. Kill retires the amend target only.
- **AC5 — Numbers.** Every € and % in this PRD sits on the number ledger (interview, csv, or named-method ESTIMATE). Missing slots stay UNKNOWN.
- **AC6 — Devil's advocate.** A signer can answer why it fails, who loses, what cannot be measured in 90 days, and why not the live control.

| Slot | Value | Source | Validate |
| --- | --- | --- | --- |
{{#each metric_rows}}
| {{name}} | {{display}} | {{source}} | {{validate_flag}} |
{{/each}}
{{#each unknown}}
| {{value}} | UNKNOWN | UNKNOWN | Validate |
{{/each}}

## Options
{{#each options}}
- **{{id}}**: {{title}} — {{summary}}
{{/each}}

Favorite going into the workshop: `{{answers.favorite_option_id}}`.

## Recommendation
{{answers.recommendation.argument}}

Chosen option: **{{favorite.title}}** (`{{answers.recommendation.option_id}}`) — {{favorite.summary}}

## Devil's advocate
Attack on the favorite before anyone signs.

- **Why it fails:** {{answers.devils_advocate.why_fails}}
- **Who loses:** {{answers.devils_advocate.who_loses}}
- **Cannot measure in 90 days:** {{answers.devils_advocate.cannot_measure}}
- **Why not the live control:** {{answers.devils_advocate.why_not_live_control}}

A signer who cannot answer these four points should pick do-nothing.

## Assumptions
- Brands and journey are as locked above. Do not widen scope in implementation without a new decide.
- Inventory may be incomplete; the author text under Current product is authoritative for what ships today.
- ESTIMATE rows must be re-validated by {{answers.approvers}} before anyone treats them as actuals.
- Unknown slots block a Finance-grade claim until the author supplies a figure or a named-method estimate.

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with a written override.
- Not a change to journeys other than {{answers.journey}}.
- Not unlabeled euro or rate guesses.
- Not a substitute for `trust-intake decide` — this PRD is the artifact of the locked option, not the decision record.

## Ask
{{answers.approvers}} to **{{answers.decision}}** {{favorite.title}} for {{answers.brands}} on {{answers.journey}}.

90-day proof: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}.
