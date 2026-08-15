from trust_intake.match_inventory import match, score_overlap

INV = {
    "controls": [
        {
            "id": "ctl-refund-static",
            "name": "Repeat claimant rule",
            "journey": "claims-cancel",
            "brands": ["foodpanda"],
        }
    ],
    "docs": [
        {
            "id": "doc-ex-1",
            "title": "Repeat claimant static rule",
            "journey": "claims-cancel",
            "brands": ["foodpanda"],
        }
    ],
}


def test_same_journey_brand_similar_title_overlaps():
    answers = {
        "title": "Repeat claimant static control",
        "journey": "claims-cancel",
        "brands": ["foodpanda"],
    }
    out = match(answers, INV)
    assert any(o["score"] >= 0.72 for o in out["overlaps"])


def test_different_journey_no_overlap():
    answers = {
        "title": "Repeat claimant static control",
        "journey": "promo",
        "brands": ["foodpanda"],
    }
    out = match(answers, INV)
    assert all(o["score"] < 0.72 for o in out["overlaps"])


def test_score_weights():
    item = {"title": "Repeat claimant static rule", "name": "Repeat claimant static rule", "journey": "claims-cancel", "brands": ["foodpanda"]}
    s = score_overlap("Repeat claimant static rule", "claims-cancel", ["foodpanda"], item)
    assert s == 1.0
