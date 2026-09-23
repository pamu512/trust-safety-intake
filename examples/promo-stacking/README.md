```
pip install -e ".[dev]"
trust-intake init --title "Promo stacking cap for foodora"
# copy answers.json into the printed run folder, then:
trust-intake parse examples/promo-stacking/loss.csv --run <id>
trust-intake run --run <id>
trust-intake approve --run <id> --confirm <sha>   # sha printed by memo
trust-intake render --run <id>
trust-intake validate --run <id>
trust-intake decide --run <id>
trust-intake render --run <id>
trust-intake validate --run <id>
```
