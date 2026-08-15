# Extrapolation

Runs only for `needed_metrics` slots that are still null. Filled `needed_metrics` are already on the ledger. Extra named facts may sit in `numbers_from_author`. Inventory is not a numeric source.

Allowed methods — no others:

| Method | When | How | Range |
| --- | --- | --- | --- |
| `run-rate` | `partial_<slot>` is on the ledger (interview name) and `elapsed_fraction` (0–1) is set | `partial / elapsed_fraction` | ±20% |
| `share-of-parent` | `parent_<slot>` on the ledger, or a parsed column that maps to the slot (`loss`/`euro`/`eur` → euro_impact, `volume`/`claim` → volume, `rate`/`pct`/`fp` → rate), plus `answers.shares.<slot>` (0–1) | `parent * share` | ±25% |
| `last-period-carry` | `facts.tables[].series` has a latest period for that measure | copy last period | ±30% |
| `peer-brand-ratio` | Peer brand measure and both brands’ GMV exist on the ledger (`gmv_<brand>` or a brand-split GMV column) | `peer * (target_gmv / peer_gmv)` | ±35% |

Refuse (do not invent) when no allowed method applies. The memo lists refused fields as `UNKNOWN — author must supply`.

Tell the author which figures are estimates before asking them to approve the memo.
