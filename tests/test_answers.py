from trust_intake.answers import empty_answers, expand_brands, validate_answers


def _complete() -> dict:
    a = empty_answers("r1", "Holdout for refunds")
    a.update(
        {
            "decision": "ship",
            "success": {"metric": "refund-abuse-rate", "direction": "down", "target": "0.4%"},
            "approvers": ["finance"],
            "brands": ["foodpanda"],
            "journey": "claims-cancel",
            "already_ships": "Manual refund queue plus a static rule on repeat claimants in 30 days.",
            "doc_action": "new",
            "doc_type": "brd",
            "options": [
                {
                    "id": "do-nothing",
                    "title": "Keep the queue",
                    "summary": "Leave the existing refund queue and static rule unchanged for this quarter.",
                    "is_do_nothing": True,
                },
                {
                    "id": "holdout",
                    "title": "Holdout + policy",
                    "summary": "Ship a holdout on refund policy changes and measure net margin before scaling.",
                    "is_do_nothing": False,
                },
            ],
            "favorite_option_id": "holdout",
            "devils_advocate": {
                "why_fails": "Holdout may starve a market of refunds and spike NPS complaints in week one.",
                "who_loses": "Good customers who need a legitimate refund during the holdout window.",
                "cannot_measure": "True fraudster displacement will not show in ninety days of one brand.",
                "why_not_live_control": "The static repeat-claimant rule already covers the loudest pattern.",
            },
            "recommendation": {
                "option_id": "holdout",
                "argument": "The locked outcome is a Finance-grade savings proof; only a holdout produces that proof.",
            },
        }
    )
    a["needed_metrics"]["volume"] = {"value": 10000, "unit": "claims"}
    a["numbers_from_author"] = [{"name": "volume", "value": 10000, "unit": "claims", "source": "interview"}]
    return a


def test_complete_answers_have_no_failures():
    assert validate_answers(_complete()) == []


def test_short_prose_fails():
    a = _complete()
    a["already_ships"] = "a queue"
    fails = validate_answers(a)
    assert any(f["path"] == "already_ships" for f in fails)


def test_missing_do_nothing_fails():
    a = _complete()
    a["options"] = [o for o in a["options"] if not o["is_do_nothing"]]
    fails = validate_answers(a)
    assert any(f["code"] == "missing_do_nothing" for f in fails)


def test_expand_all_brands():
    assert expand_brands(["all"]) == ["foodora", "foodpanda", "yemeksepeti"]


def test_wrong_types_are_bad_type():
    for key, value in (
        ("success", "refund-abuse-rate"),
        ("recommendation", "ship it"),
        ("options", "do-nothing"),
    ):
        a = _complete()
        a[key] = value
        fails = validate_answers(a)
        assert any(f["code"] == "bad_type" and f["path"] == key for f in fails), key
