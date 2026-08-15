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

## Solution
{{answers.recommendation.argument}}

## Journeys
{{answers.journey}}

## In scope
{{answers.already_ships}}

## Out of scope
Amend target {{answers.amend_target_id}} is out of scope unless doc_action is amend.

## Acceptance criteria
{{answers.success.metric}} {{answers.success.direction}} {{answers.success.target}}
Volume {{ledger.volume}}

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with override.
