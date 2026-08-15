# Product inventory

Generated. Edit `product-inventory.yaml`.

## Stack

| id | name | layer | notes |
| --- | --- | --- | --- |
| rules | Rules engine | decisioning | Parameterize before new PRDs |
| ml-score | ML risk score | decisioning | Maturity to map |
| sql-wh | SQL warehouse | data |  |
| looker | Looker | reporting |  |
| manual-inv | Manual investigations | ops |  |

## Controls

| id | name | type | journey | brands | status | owner |
| --- | --- | --- | --- | --- | --- | --- |
| ctl-refund-static | Repeat claimant rule | rule | claims-cancel | foodpanda | live | ops |

## Docs

| id | type | title | status | journey | brands |
| --- | --- | --- | --- | --- | --- |
| doc-ex-1 | brd | Repeat claimant static rule | shipped | claims-cancel | foodpanda |
