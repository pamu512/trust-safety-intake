# {{answers.title}}

## Locked outcome
- Decision: {{answers.decision}}
- Document action: {{answers.doc_action}} (amend target: {{answers.amend_target_id}})
- Brands: {{answers.brands}}
- Journey: {{answers.journey}}
- 90-day success: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}
- Approvers who must say yes: {{answers.approvers}}

## Executive summary
This BRD asks {{answers.approvers}} to {{answers.decision}} **{{favorite.title}}** on {{answers.brands}} / {{answers.journey}}.

{{answers.recommendation.argument}}

Current product: {{answers.already_ships}}

90-day success is {{answers.success.metric}} {{answers.success.direction}} ({{answers.success.target}}). Volume in scope: {{ledger.volume}}.

## Problem
{{answers.already_ships}}

This is a {{answers.doc_action}} on the {{answers.journey}} journey for {{answers.brands}}. The decision this document must unlock is **{{answers.decision}}**. If we do nothing, the do-nothing option remains: the live process stays as described above and we accept the current loss, rate, and volume on the ledger.

## Current product
What already ships (author): {{answers.already_ships}}

Inventory overlaps at or above the match threshold:

{{#each overlap_rows}}
- {{kind}} `{{id}}`: {{title}} (score {{score}})
{{/each}}

If the list above is empty, match found no live control or existing doc at threshold. Still treat the author text as the source for what ships — inventory is not complete.

Doc action is `{{answers.doc_action}}`. Default on overlap is amend, not a parallel BRD.

## Business requirements
These must be testable in 90 days.

- **R1 — Chosen option.** Implement **{{favorite.title}}** on {{answers.brands}} {{answers.journey}}: {{favorite.summary}}
- **R2 — Success metric.** {{answers.success.metric}} must go {{answers.success.direction}} to {{answers.success.target}}. {{answers.approvers}} sign that metric.
- **R3 — Volume.** Operate on the ledger volume of {{ledger.volume}} (source on the metrics table). Do not invent a second volume.
- **R4 — Action type.** `doc_action` is {{answers.doc_action}}. If amend, extend `{{answers.amend_target_id}}` and do not stand up a parallel control. If new, do not silently replace a live control. If kill, retire the amend target only.
- **R5 — Options.** Keep a runnable do-nothing path. Do not ship a third option that was not scored in this BRD.
- **R6 — Numbers.** Every € and % in this document must sit on the number ledger (interview, csv, or named-method ESTIMATE). Missing slots stay UNKNOWN.

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

## Metrics
- Primary: {{answers.success.metric}} {{answers.success.direction}} ({{answers.success.target}})
- Volume: {{ledger.volume}}

| Slot | Value | Source | Validate |
| --- | --- | --- | --- |
{{#each metric_rows}}
| {{name}} | {{display}} | {{source}} | {{validate_flag}} |
{{/each}}
{{#each unknown}}
| {{value}} | UNKNOWN | UNKNOWN | Validate |
{{/each}}

Use the named slots (`volume`, `rate`, `euro_impact`, …) for the ask. CSV rollups are supporting evidence, not a second set of targets.

## Assumptions
- Brands and journey are as locked above. Do not widen scope in implementation without a new decide.
- Inventory may be incomplete; the author text under Current product is authoritative for what ships today.
- ESTIMATE rows must be re-validated by {{answers.approvers}} before anyone treats them as actuals.
- Unknown slots block a Finance-grade claim until the author supplies a figure or a named-method estimate.

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with a written override.
- Not a change to journeys other than {{answers.journey}}.
- Not unlabeled euro or rate guesses.
- Not a substitute for `trust-intake decide` — this BRD is the artifact of the locked option, not the decision record.

## Ask
{{answers.approvers}} to **{{answers.decision}}** {{favorite.title}} for {{answers.brands}} on {{answers.journey}}.

90-day proof: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}.
