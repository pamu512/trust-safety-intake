from __future__ import annotations

NEEDED_SLOTS = (
    "volume",
    "rate",
    "euro_impact",
    "trend",
    "baseline",
    "cx_fp_cost",
)


def empty_metric() -> dict:
    return {"value": None, "unit": None}


def empty_answers(run_id: str, title: str) -> dict:
    return {
        "run_id": run_id,
        "title": title,
        "decision": None,
        "success": {"metric": None, "direction": None, "target": None},
        "approvers": [],
        "brands": [],
        "journey": None,
        "already_ships": "",
        "doc_action": None,
        "amend_target_id": None,
        "duplicate_override": None,
        "elapsed_fraction": None,
        "shares": {},
        "doc_type": None,
        "needed_metrics": {slot: empty_metric() for slot in NEEDED_SLOTS},
        "numbers_from_author": [],
        "options": [],
        "favorite_option_id": None,
        "devils_advocate": {
            "why_fails": "",
            "who_loses": "",
            "cannot_measure": "",
            "why_not_live_control": "",
        },
        "recommendation": {"option_id": None, "argument": ""},
    }
