# {{answers.title}}

## Locked outcome
- Decision: {{answers.decision}}
- Document action: {{answers.doc_action}} (amend target: {{answers.amend_target_id}})
- Brands: {{answers.brands}}
- Journey: {{answers.journey}}
- 90-day success: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}
- Approvers who must say yes: {{answers.approvers}}

## Executive summary
This business case asks {{answers.approvers}} to {{answers.decision}} **{{favorite.title}}** on {{answers.brands}} / {{answers.journey}}.

{{answers.recommendation.argument}}

Current product: {{answers.already_ships}}

Cost in scope: {{ledger.euro_impact}}. Volume {{ledger.volume}} at {{ledger.rate}}. 90-day success is {{answers.success.metric}} {{answers.success.direction}} ({{answers.success.target}}).

## Current product
What already ships (author): {{answers.already_ships}}

Inventory overlaps at or above the match threshold:

{{#each overlap_rows}}
- {{kind}} `{{id}}`: {{title}} (score {{score}})
{{/each}}

If the list above is empty, match found no live control or existing doc at threshold. Still treat the author text as the source for what ships — inventory is not complete.

Doc action is `{{answers.doc_action}}`. Default on overlap is amend, not a parallel case.

## Cost
{{ledger.euro_impact}} on the ledger (`euro_impact`). That is the figure {{answers.approvers}} are asked to treat as the 90-day money case.

- Do not introduce a second euro figure in the ask.
- If the row is ESTIMATE, it is a named-method range, not an actual. Re-validate before treating it as booked savings.
- `doc_action` is {{answers.doc_action}}. Amend spends against `{{answers.amend_target_id}}`. New does not silently replace a live control.

| Slot | Value | Source | Validate |
| --- | --- | --- | --- |
{{#each metric_rows}}
| {{name}} | {{display}} | {{source}} | {{validate_flag}} |
{{/each}}
{{#each unknown}}
| {{value}} | UNKNOWN | UNKNOWN | Validate |
{{/each}}

## Impact
{{ledger.volume}} at {{ledger.rate}}.

- Primary metric: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}
- Population: ledger volume {{ledger.volume}} on {{answers.brands}} {{answers.journey}}
- Chosen option **{{favorite.title}}**: {{favorite.summary}}
- If we do nothing, we accept the current cost and rate on the ledger.

## Options comparison
{{#each options}}
- **{{id}}**: {{title}} — {{summary}}
{{/each}}

Favorite going into the workshop: `{{answers.favorite_option_id}}`.

Do-nothing is in the table. A case that cannot beat do-nothing on a signed 90-day metric should not be funded.

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
- Brands and journey are as locked above. Do not widen scope without a new decide.
- Inventory may be incomplete; the author text under Current product is authoritative for what ships today.
- ESTIMATE rows must be re-validated by {{answers.approvers}} before anyone treats them as actuals.
- Unknown slots block a Finance-grade claim until the author supplies a figure or a named-method estimate.

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with a written override.
- Not a change to journeys other than {{answers.journey}}.
- Not unlabeled euro or rate guesses.
- Not a substitute for `trust-intake decide` — this case is the artifact of the locked option, not the decision record.

## Ask
{{answers.approvers}} to **{{answers.decision}}** {{favorite.title}} for {{answers.brands}} on {{answers.journey}}.

Money: {{ledger.euro_impact}}. Volume {{ledger.volume}} at {{ledger.rate}}.

90-day proof: {{answers.success.metric}} {{answers.success.direction}} — {{answers.success.target}}.
