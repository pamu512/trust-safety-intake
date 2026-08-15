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


def _needed(**overrides: dict) -> dict:
    slots = {
        "volume": {"value": 1, "unit": "claims"},
        "rate": {"value": 0.1, "unit": None},
        "euro_impact": {"value": None, "unit": "EUR"},
        "trend": {"value": 0, "unit": None},
        "baseline": {"value": 0, "unit": None},
        "cx_fp_cost": {"value": 0, "unit": None},
    }
    slots.update(overrides)
    return slots


def test_peer_brand_ratio_strips_full_slot_prefix():
    answers = {
        "needed_metrics": _needed(),
        "elapsed_fraction": None,
        "numbers_from_author": [
            {"name": "euro_impact_foodora", "value": 100, "unit": "EUR", "source": "interview"},
            {"name": "gmv_foodpanda", "value": 200, "unit": "EUR", "source": "interview"},
            {"name": "gmv_foodora", "value": 100, "unit": "EUR", "source": "interview"},
        ],
        "shares": {},
        "brands": ["foodpanda"],
    }
    out = extrapolate(answers, {"derived": [], "tables": []})
    est = next(e for e in out["estimates"] if e["name"] == "euro_impact")
    assert est["method"] == "peer-brand-ratio"
    assert est["value"] == 200


def test_foodpanda_column_does_not_map_to_rate():
    answers = {
        "needed_metrics": _needed(
            volume={"value": 1, "unit": "claims"},
            rate={"value": None, "unit": None},
            euro_impact={"value": 1, "unit": "EUR"},
        ),
        "elapsed_fraction": None,
        "numbers_from_author": [],
        "shares": {},
        "brands": ["foodora"],
    }
    facts = {
        "derived": [],
        "tables": [
            {
                "name": "brands",
                "series": [{"values": {"foodpanda": 0.4, "foodpanda_gmv": 9_000_000}}],
            }
        ],
    }
    out = extrapolate(answers, facts)
    assert "rate" in out["unknown"]
    assert not any(e["name"] == "rate" for e in out["estimates"])
