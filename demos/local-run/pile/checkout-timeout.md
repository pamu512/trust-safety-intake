# Checkout timeout retry for yemeksepeti

## Locked outcome
- Decision: ship
- 90-day success: checkout-timeout-loss down Finance-signed reduction
- Approvers: finance, product

## Assumptions
| Claim | Source | Validate |
| --- | --- | --- |

| loss.loss_eur.sum = 3100000  | csv |  |

| loss.orders.sum = 120000  | csv |  |

| loss.loss_eur.pop = 0.06666666666666667  | csv |  |

| loss.orders.pop = 0.06896551724137931  | csv |  |

| loss.yemeksepeti.loss_eur.share = 1  | csv |  |

| loss.yemeksepeti.orders.share = 1  | csv |  |

| volume = 120000 orders | interview |  |

| rate = 0.015 % | interview |  |

| euro_impact = 3200000 EUR | interview |  |


## Options

- do-nothing: Keep one retry — Leave the single payment retry and current timeout window unchanged this quarter.

- second-retry: Second retry + hold — Add a second retry after 30 seconds and hold the basket so the customer does not re-order.


## Devil's advocate
- Why it fails: A second retry can double-charge and create a claims spike that eats the saved checkout GMV.
- Who loses: Customers billed twice and the claims team that has to unwind those payments.
- Cannot measure in 90 days: Net GMV after chargebacks will not be clean in ninety days of one brand.
- Why not the live control: The existing single retry already recovers the obvious drop-offs without a double-charge risk.

## Recommendation
The locked outcome is a Finance-grade cut in timeout loss; a measured second retry is the only option that can prove it.

## Cost
€3.2M

## Impact
120000 at 1.50%

## Options comparison

- do-nothing: Keep one retry — Leave the single payment retry and current timeout window unchanged this quarter.

- second-retry: Second retry + hold — Add a second retry after 30 seconds and hold the basket so the customer does not re-order.


## Ask
ship
