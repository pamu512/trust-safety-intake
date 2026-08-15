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


BRANDS = ("foodora", "foodpanda", "yemeksepeti")
JOURNEYS = ("account", "promo", "checkout", "claims-cancel", "payout", "cross-journey")
DECISIONS = ("ship", "fund", "stop", "change-policy", "align")
DOC_ACTIONS = ("new", "amend", "kill")
DOC_TYPES = ("brd", "prd", "business-case", "case-study")
DIRECTIONS = ("up", "down", "hold")
PROSE_MIN = 40
PROSE_PATHS = (
    "already_ships",
    "devils_advocate.why_fails",
    "devils_advocate.who_loses",
    "devils_advocate.cannot_measure",
    "devils_advocate.why_not_live_control",
    "recommendation.argument",
)


def _get(data: dict, dotted: str):
    cur: object = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def expand_brands(brands: list[str]) -> list[str]:
    if "all" in brands:
        return list(BRANDS)
    return [b for b in brands if b in BRANDS]


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def validate_answers(answers: dict) -> list[dict]:
    fails: list[dict] = []
    required = (
        "run_id",
        "title",
        "decision",
        "success",
        "approvers",
        "brands",
        "journey",
        "already_ships",
        "doc_action",
        "doc_type",
        "needed_metrics",
        "options",
        "favorite_option_id",
        "devils_advocate",
        "recommendation",
    )
    for key in required:
        if key not in answers:
            fails.append(_fail("missing_key", key, f"missing {key}"))
    if fails:
        return fails
    if answers["decision"] not in DECISIONS:
        fails.append(_fail("bad_enum", "decision", "invalid decision"))
    if answers["journey"] not in JOURNEYS:
        fails.append(_fail("bad_enum", "journey", "invalid journey"))
    if answers["doc_action"] not in DOC_ACTIONS:
        fails.append(_fail("bad_enum", "doc_action", "invalid doc_action"))
    if answers["doc_type"] not in DOC_TYPES:
        fails.append(_fail("bad_enum", "doc_type", "invalid doc_type"))
    success = answers["success"]
    if not success.get("metric") or success.get("direction") not in DIRECTIONS:
        fails.append(_fail("bad_success", "success", "metric and direction required"))
    if not answers["approvers"]:
        fails.append(_fail("missing_approvers", "approvers", "at least one approver"))
    if not expand_brands(answers.get("brands") or []):
        fails.append(_fail("missing_brands", "brands", "at least one brand"))
    for path in PROSE_PATHS:
        val = _get(answers, path)
        if not isinstance(val, str) or len(val.strip()) < PROSE_MIN:
            fails.append(_fail("short_prose", path, f"{path} must be >= {PROSE_MIN} chars"))
    for opt in answers["options"]:
        if len(str(opt.get("summary") or "")) < PROSE_MIN:
            fails.append(_fail("short_prose", f"options.{opt.get('id')}.summary", "option summary too short"))
    if not any(o.get("is_do_nothing") for o in answers["options"]):
        fails.append(_fail("missing_do_nothing", "options", "one option must be do-nothing"))
    ids = {o.get("id") for o in answers["options"]}
    if answers["favorite_option_id"] not in ids:
        fails.append(_fail("bad_option", "favorite_option_id", "favorite not in options"))
    if answers["recommendation"].get("option_id") not in ids:
        fails.append(_fail("bad_option", "recommendation.option_id", "recommendation not in options"))
    if answers["doc_action"] == "new":
        override = answers.get("duplicate_override")
        # override checked later against overlaps; here only length if present
        if override is not None and len(str(override).strip()) < PROSE_MIN:
            fails.append(_fail("short_override", "duplicate_override", "override must be >= 40 chars"))
    return fails
