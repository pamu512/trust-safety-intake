# Extrapolation

Runs only for `needed_metrics` slots that are still null after `facts.derived` and `numbers_from_author` are applied. Inputs to a method must already be on the ledger (csv or interview). Inventory is not a numeric source.

Allowed methods — no others:

| Method | When | How | Range |
| --- | --- | --- | --- |
| `run-rate` | A partial-period value and `elapsed_fraction` (0–1) exist on the ledger or in `answers.elapsed_fraction` | `(value / elapsed_fraction) * 1.0` | ±20% |
| `share-of-parent` | Child missing; parent value and a share (0–1) exist on the ledger or in `answers.shares.<child>` | `parent * share` | ±25% |
| `last-period-carry` | `facts.tables[].series` has a latest period for that measure | copy last period | ±30% |
| `peer-brand-ratio` | Peer brand measure and both brands’ GMV exist on the ledger | `peer * (target_gmv / peer_gmv)` | ±35% |

Refuse (do not invent) when no allowed method applies. The memo lists refused fields as `UNKNOWN — author must supply`.

Tell the author which figures are estimates before asking them to approve the memo.
