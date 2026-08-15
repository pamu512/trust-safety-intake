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
