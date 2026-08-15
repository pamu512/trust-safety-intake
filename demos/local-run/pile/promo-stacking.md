# Promo stacking cap for foodora

## Locked outcome
- Decision: ship
- 90-day success: promo-stack-rate down Finance-signed reduction
- Approvers: finance, brand-pnl

## Assumptions
| Claim | Source | Validate |
| --- | --- | --- |

| loss.loss_eur.sum = 3200000  | csv |  |

| loss.orders.sum = 92000  | csv |  |

| loss.loss_eur.pop = 0.2857142857142857  | csv |  |

| loss.orders.pop = 0.19047619047619047  | csv |  |

| loss.loss_eur.yoy = 0.2857142857142857  | csv |  |

| loss.orders.yoy = 0.19047619047619047  | csv |  |

| loss.foodora.loss_eur.share = 1  | csv |  |

| loss.foodora.orders.share = 1  | csv |  |

| volume = 50000 orders | interview |  |

| rate = 0.08 % | interview |  |

| euro_impact = 1800000 EUR | interview |  |


## Options

- do-nothing: Keep the weekly review — Leave the manual promo cap and weekly ops review unchanged for this quarter.

- hard-cap: Hard stack cap — Ship a hard cap of one paid promo per checkout and measure stack rate before widening.


## Devil's advocate
- Why it fails: A hard cap will block legitimate multi-voucher campaigns and spike support tickets in week one.
- Who loses: Growth and brand-PnL teams that rely on stacked acquisition codes in DE and AT.
- Cannot measure in 90 days: True displacement of stacking rings will not show in ninety days of one brand.
- Why not the live control: The weekly review already catches the loudest stacks after the order is placed.

## Recommendation
The locked outcome is a Finance-grade cut in stack rate; only a hard cap produces a measurable 90-day proof.

## Problem
Foodora has a manual promo cap and a weekly ops review. Last year showed 8% stacked-promo abuse and about €1.8M loss on the promo journey.

## Business requirements
- Requirement text must be testable. Amend target: 

## Metrics
- Primary: promo-stack-rate
- Volume: 50000

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with override.
