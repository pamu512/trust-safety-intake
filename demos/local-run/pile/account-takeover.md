# Account takeover step-up for foodpanda

## Locked outcome
- Decision: fund
- 90-day success: ato-rate down Hold or better vs last quarter
- Approvers: product, eng

## Assumptions
| Claim | Source | Validate |
| --- | --- | --- |

| volume = 20000 flags | interview |  |

| rate = 0.03 % | interview |  |

| euro_impact = 900000 EUR | interview |  |


## Options

- do-nothing: Keep the review queue — Leave the device-graph queue and current step-up rules unchanged this quarter.

- step-up: Step-up on new device — Add a step-up challenge on new-device login and measure ATO rate plus false-positive cost.

- kill-queue: Drop the queue — Retire the manual device-graph queue and rely only on the existing password reset flow.


## Devil's advocate
- Why it fails: Step-up will bounce good riders on shared phones and inflate login drop-off in SG and HK.
- Who loses: Honest customers on family devices and the CX team that absorbs the extra tickets.
- Cannot measure in 90 days: True ATO displacement versus password-reset fraud will not show in ninety days.
- Why not the live control: The device-graph queue already covers the loudest takeover pattern after the fact.

## Recommendation
The locked outcome is a funded experiment on ATO rate; only a step-up trial produces that 90-day signal.

## Solution
The locked outcome is a funded experiment on ATO rate; only a step-up trial produces that 90-day signal.

## Journeys
account

## In scope
Foodpanda runs a device-graph review queue. Last quarter logged 20000 flags at a 3% takeover rate, about €900k loss on the account journey.

## Out of scope
Amend target  is out of scope unless doc_action is amend.

## Acceptance criteria
ato-rate
Volume 20000

## Non-goals
- Not a rebuild of live controls unless `doc_action` is new with override.
