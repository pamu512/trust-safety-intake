# BRD portfolio triage — Design

**Date:** 2026-08-15  
**Repo:** `trust-safety-intake`  
**Status:** Draft for review  
**Audience:** Pandora product managers reviewing a pile of submitted BRDs.

## 1. Purpose

A PM drops a folder of submitted BRDs (markdown, Word, PDF, Confluence HTML). One CLI command scores the pile and says which to unify, which to deprioritise, and which are high priority because the pain spans brands or markets.

The agent does not rank by vibe. `trust-intake triage` owns extract, cluster, labels, and the memo.

## 2. Non-goals

- Not a Jira / Confluence sync.
- Not an embeddings or ML clusterer.
- Does not invent brands, markets, or euros. Empty extract → `extraction-gap`, not a guess.
- Does not write or rewrite the submitted BRDs.
- Does not replace single-doc intake (`init` … `validate`).

## 3. Command

```
trust-intake triage <folder> [--min-euro 100000] [--inventory inventory/product-inventory.yaml] [--markets inventory/markets.yaml]
```

Writes:

- `<folder>/triage.json` — cards, clusters, labels, reasons
- `<folder>/triage.md` — PM memo

Exit `0` if at least one file was scored. Exit `1` if the folder has no readable BRDs. Exit `2` on missing folder / IO.

Unsupported suffixes are skipped and listed under `warnings[]`. They do not fail the batch.

## 4. Inputs

| Suffix | Reader |
| --- | --- |
| `.md` `.txt` | UTF-8 text |
| `.html` `.htm` | Strip tags; keep text |
| `.docx` | `python-docx` |
| `.pdf` | `pypdf` |

Optional sidecar: `<stem>.meta.json` next to the file.

```json
{ "brands": ["foodpanda"], "markets": ["SG", "HK"], "journey": "claims-cancel" }
```

Sidecar values win over extract for those keys. Unknown sidecar keys are ignored.

## 5. Card

```yaml
id: string                 # slug from filename
path: string
title: string              # first heading, else filename stem
brands: [foodora | foodpanda | yemeksepeti]
markets: [string]          # ISO codes from markets.yaml
journey: account | promo | checkout | claims-cancel | payout | cross-journey | unknown
euro_impact: {value: number | null, unit: EUR, source: extract | sidecar | missing}
volume: {value: number | null, unit: string | null, source: extract | sidecar | missing}
rate: {value: number | null, unit: '%', source: extract | sidecar | missing}
labels: [unify | deprioritise | high-priority | extraction-gap]
reasons: [string]          # machine codes, see §7
cluster_id: string | null
inventory_overlaps: [{id, kind, title, score}]
```

## 6. Extract (deterministic)

- **title** — first markdown `#` / HTML `<h1>` / first non-empty line, else file stem.
- **brands** — word-boundary match on `foodora`, `foodpanda`, `yemeksepeti`. Phrases `all brands` / `all three brands` → all three.
- **markets** — allowlist in `inventory/markets.yaml`. Match ISO code (word-boundary) or any listed alias (case-insensitive).
- **journey** — if exactly one of the six journey tokens appears, use it; if several, `cross-journey`; if none, `unknown`.
- **quantities** — run the existing ledger scanner on the extracted text. First `€`/`EUR` amount → `euro_impact`. First `%` → `rate`. First allowlisted unit (`orders`, `claims`, `flags`, `payouts`) → `volume`. If the same line contains `estimate`, `approx`, or `~`, source stays `extract` and the memo marks it `ESTIMATE`.

No LLM. No inventory numbers copied in.

If `brands` is empty and `markets` is empty after sidecar: add label `extraction-gap` and reason `extraction-gap`.

## 7. Labels

A card may hold more than one label. Reasons are always listed.

### unify

Pairwise score against every other submitted card.

When both journeys are known (not `unknown`):

`0.4 * journey_exact + 0.3 * brand_jaccard + 0.3 * difflib_title`

When either journey is `unknown` (common in Word/PDF dumps):

`0.5 * brand_jaccard + 0.5 * difflib_title`

Threshold `>= 0.72`. Clusters are connected components. Each member gets `unify` and `cluster_id`. Memo recommendation: keep one surviving BRD (highest euro_impact, else most brands+markets); others amend/merge into it.

`ponytail:` first extracted `€` is treated as impact. Wrong hit → sidecar `euro_impact`. Upgrade: labeled “annual impact” / “exposure” lines if false positives show up.

Market overlap is reported on the cluster; it does not change the 0.72 threshold.

### deprioritise

Any of these reasons (all that apply):

| Code | When |
| --- | --- |
| `thin` | exactly 1 brand AND exactly 1 market AND (`euro_impact` missing or `< --min-euro`) |
| `already-ships` | inventory overlap `>= 0.72` (existing `score_overlap` vs controls + docs) |
| `no-numbers` | `euro_impact`, `volume`, and `rate` are all missing |

Default `--min-euro` is `100000`.

### high-priority

`len(brands) >= 2` OR `len(markets) >= 2`.

`thin` and `high-priority` cannot both apply (`thin` requires one brand and one market).

`high-priority` + `no-numbers` is allowed: cross-cutting but unmeasured. Memo says “priority, then demand numbers.”

### Combined

- unify + high-priority → must-do merge (same pain, many brands/markets).
- unify + deprioritise → merge first, then drop the thin copies.
- extraction-gap alone → PM fills sidecar and re-runs; do not deprioritise solely for that.

## 8. Markets file

`inventory/markets.yaml` is human-edited.

```yaml
markets:
  - id: DE
    aliases: [Germany, Deutschland]
  - id: SG
    aliases: [Singapore]
  # … seed: DE AT NL SE NO FI DK SG HK MY TH TW PH PK BD TR
```

`trust-intake inventory-lint` fails on duplicate ids or empty ids. Unknown extracted tokens are ignored (not invented).

## 9. Outputs

`triage.md` sections, in this order:

1. **High priority** — cards with `high-priority`, sorted by brand count then market count then euro_impact desc. Show brand/market spread.
2. **Unify** — one subsection per cluster: members, pairwise scores, surviving BRD, market union.
3. **Deprioritise** — cards with `deprioritise`, grouped by reason codes.
4. **Extraction gaps** — files that need a sidecar.
5. **Warnings** — skipped suffixes, unreadable files.

`triage.json` is the machine source of truth. The markdown is rendered from it. Do not hand-edit the markdown.

## 10. Dependencies

Add `python-docx` and `pypdf`. No other new dependencies. Reuse `score_overlap`, `scan_quantities`, `load_inventory`, `lint_inventory`.

## 11. Tests

- Markdown + html + docx + pdf each produce a card (golden snippets).
- `all three brands` → three brands.
- Market alias `Singapore` → `SG`.
- Two similar titles, same journey+brand → one unify cluster.
- 1 brand, 1 market, €50k, `--min-euro 100000` → `thin`.
- 2 brands, no numbers → `high-priority` + `no-numbers`.
- Card matching seed `ctl-refund-static` → `already-ships`.
- Sidecar overrides extracted brands.
- `.xlsx` in the folder → warning, not a crash.
- Empty folder → exit 1.

## 12. Success

A PM can drop a mixed folder, run one command, and get a memo that (a) names unify clusters, (b) lists deprioritise reasons, (c) ranks cross-brand/cross-market BRDs, with every euro tagged extract/sidecar/missing.
