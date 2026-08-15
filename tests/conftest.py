import pytest

from trust_intake.answers import empty_answers


@pytest.fixture
def complete_answers() -> dict:
    a = empty_answers("r1", "Holdout for refunds")
    a.update(
        {
            "decision": "ship",
            "success": {"metric": "refund-abuse-rate", "direction": "down", "target": "Finance-signed reduction"},
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
