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

{{ledger.volume}}
