from trust_intake.ledger import build_ledger, scan_quantities, unresolved_quantities


def test_build_unions_three_sources():
    facts = {"derived": [{"name": "loss.sum", "value": 228, "unit": "EUR", "source": "csv", "method": "sum"}]}
    answers = {"numbers_from_author": [{"name": "volume", "value": 10000, "unit": "claims", "source": "interview"}]}
    estimates = {"estimates": [{"name": "euro_impact", "value": 2500000, "unit": "EUR", "source": "ESTIMATE"}]}
    names = {r["name"] for r in build_ledger(facts, answers, estimates)}
    assert names == {"loss.sum", "volume", "euro_impact"}


def test_needed_metrics_land_on_ledger_without_dual_write():
    answers = {"needed_metrics": {"volume": {"value": 10000, "unit": "claims"}, "euro_impact": {"value": 2500000, "unit": "EUR"}}}
    names = {r["name"]: r for r in build_ledger({"derived": []}, answers, {"estimates": []})}
    assert names["volume"]["value"] == 10000
    assert names["euro_impact"]["value"] == 2_500_000
    assert names["volume"]["source"] == "interview"


def test_scan_ignores_ninety_day():
    tokens = scan_quantities("In 90-day window refunds are €2.5M at 12% of claims.")
    values = {v for _, v in tokens}
    assert 2_500_000 in values
    assert 0.12 in values
    assert 90 not in values


def test_unresolved_extra_euro():
    ledger = [{"name": "euro_impact", "value": 2_500_000, "unit": "EUR", "source": "interview"}]
    leftover = unresolved_quantities("Savings of €2.5M plus a stray €12M.", ledger)
    assert leftover == ["€12M"]
