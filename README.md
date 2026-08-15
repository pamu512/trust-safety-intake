# Trust Safety Intake

A portable GitHub repo Pandora drops into Cursor, Claude, or any agent that reads `SKILL.md`. It turns a fuzzy Trust & Safety ask into a decision-ready BRD, PRD, business case, or case study.

The agent only interviews. The `trust-intake` CLI owns init, CSV/XLSX parse, inventory overlap, named-method extrapolation, workshop memo, approve gate, template render, number ledger, and hard validate. Drafts cannot exist without a workshop memo and `APPROVED`.

The agent skill lives in [`skills/trust-intake/`](skills/trust-intake/).

## Install

Python 3.11+.

```
pip install -e ".[dev]"
```

(`pip install -e .` is enough to run the CLI; `[dev]` adds pytest.)

## Golden example

Anonymized refund-abuse run (fake brand codes, fake euros):

```
pip install -e ".[dev]"
trust-intake init --title "Refund holdout for repeat claimants"
# copy answers.json into the printed run folder, then:
trust-intake parse examples/refund-abuse/loss.csv --run <id>
trust-intake run --run <id>
trust-intake approve --run <id>
trust-intake render --run <id>
trust-intake validate --run <id>
```

`validate` must exit 0. `run` stops after `memo`; it does not approve or render.

## Inventory

`inventory/product-inventory.yaml` is the only file humans edit. It is the anti-duplicate source of truth: brands, journeys, stack, live controls, existing docs.

After editing the YAML:

```
trust-intake inventory-lint
trust-intake inventory-render
```

`inventory/product-inventory.md` is generated. Do not edit it by hand.

The agent still asks what already ships today. Inventory is not a substitute for the interview.
