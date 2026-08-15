# Decide + inventory — Design

**Date:** 2026-08-15  
**Status:** Approved (approach A)

## Purpose

A recorded decision is the product. The BRD is an artifact. Inventory updates when a decision is recorded. The agent is not done until `decide` exits 0. Rules/skills only — no hooks.

## Commands

```
trust-intake decide --run <id>
trust-intake decide --triage <folder>
```

Exactly one of `--run` / `--triage`. Writes `decision.json`, upserts `product-inventory.yaml`, regenerates `product-inventory.md`.

## Write-path (`--run`)

Requires valid `APPROVED` (memo sha) and valid `answers.json`.

Locks `recommendation.option_id` plus `doc_action`.

Inventory:

- `new` → upsert `docs[]` id `doc-<run_id>`, status `approved`
- `amend` → update `amend_target_id` (required)
- `kill` → set target `amend_target_id` status `killed` (required)
- recommended option is do-nothing and action is not `kill` → decision only, no doc write

## Triage-path (`--triage`)

Requires `<folder>/triage.json`. Does not run extract again.

Inventory:

- unify survivor, if not `already-ships` → upsert `doc-<card.id>`, status `open`
- unify losers already in inventory → status `killed`
- `high-priority` and not `deprioritise` → upsert `open`
- thin / no-numbers / extraction-gap / already-ships → no new row

## `decision.json`

```json
{
  "id": "dec-<run_id|folder>",
  "source": "run|triage",
  "locked": {},
  "inventory_writes": [{"op": "upsert_doc|kill_doc|none", "id": "doc-..."}]
}
```

Write-path: `runs/<id>/decision.json`. Triage-path: `<folder>/decision.json`.

## Chat BRD

`AGENTS.md`, `.cursor/rules`, `SKILL.md`, `GEMINI.md`: first action on a BRD ask is `init`; never write BRD markdown; not done until `decide` exits 0. No hooks.
