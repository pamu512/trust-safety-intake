from trust_intake.extrapolate import extrapolate


def test_run_rate_half_year():
    answers = {
        "needed_metrics": {
            "volume": {"value": None, "unit": "claims"},
            "rate": {"value": 0.1, "unit": None},
            "euro_impact": {"value": None, "unit": "EUR"},
            "trend": {"value": None, "unit": None},
            "baseline": {"value": None, "unit": None},
            "cx_fp_cost": {"value": None, "unit": None},
        },
        "elapsed_fraction": 0.5,
        "numbers_from_author": [
            {"name": "partial_euro_impact", "value": 1_000_000, "unit": "EUR", "source": "interview"}
        ],
        "shares": {},
        "brands": ["foodpanda"],
    }
    facts = {"derived": [], "tables": []}
    # map: if euro_impact null and partial_euro_impact + elapsed_fraction exist, run-rate
    out = extrapolate(answers, facts)
    est = next(e for e in out["estimates"] if e["name"] == "euro_impact")
    assert est["method"] == "run-rate"
    assert est["value"] == 2_000_000
    assert est["range"]["low"] == 1_600_000
    assert est["range"]["high"] == 2_400_000
    assert est["source"] == "ESTIMATE"


def test_refuse_when_no_method():
    answers = {
        "needed_metrics": {
            "volume": {"value": None, "unit": "claims"},
            "rate": {"value": None, "unit": None},
            "euro_impact": {"value": None, "unit": "EUR"},
            "trend": {"value": None, "unit": None},
            "baseline": {"value": None, "unit": None},
            "cx_fp_cost": {"value": None, "unit": None},
        },
        "elapsed_fraction": None,
        "numbers_from_author": [],
        "shares": {},
        "brands": ["foodpanda"],
    }
    out = extrapolate(answers, {"derived": [], "tables": []})
    assert out["estimates"] == []
    assert "volume" in out["unknown"]
    assert "euro_impact" in out["unknown"]
