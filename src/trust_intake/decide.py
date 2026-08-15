from __future__ import annotations

import copy
import json
from pathlib import Path

from trust_intake.answers import JOURNEYS, expand_brands, validate_answers
from trust_intake.render import is_approved
from trust_intake.run_store import read_json, slugify


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _doc_id_run(run_id: str) -> str:
    return f"doc-{slugify(run_id)}"


def _doc_id_card(card_id: str) -> str:
    return f"doc-{slugify(card_id)}"


def _find_doc(inventory: dict, doc_id: str) -> dict | None:
    for doc in inventory.get("docs") or []:
        if doc.get("id") == doc_id:
            return doc
    return None


def _upsert_doc(inventory: dict, doc: dict) -> str:
    docs = inventory.setdefault("docs", [])
    for i, existing in enumerate(docs):
        if existing.get("id") == doc["id"]:
            merged = dict(existing)
            merged.update(doc)
            docs[i] = merged
            return "upsert_doc"
    docs.append(doc)
    return "upsert_doc"


def _kill_doc(inventory: dict, doc_id: str) -> bool:
    doc = _find_doc(inventory, doc_id)
    if not doc:
        return False
    doc["status"] = "killed"
    return True


def _is_do_nothing(answers: dict) -> bool:
    rec_id = (answers.get("recommendation") or {}).get("option_id")
    for opt in answers.get("options") or []:
        if isinstance(opt, dict) and opt.get("id") == rec_id and opt.get("is_do_nothing"):
            return True
    return False


def _doc_from_answers(answers: dict, doc_id: str, status: str) -> dict:
    return {
        "id": doc_id,
        "type": answers["doc_type"],
        "title": answers["title"],
        "status": status,
        "journey": answers["journey"],
        "brands": expand_brands(answers.get("brands") or []),
        "link": answers.get("run_id") or "",
    }


def _card_doc(card: dict, status: str) -> dict | None:
    brands = expand_brands(card.get("brands") or [])
    if not brands:
        return None
    journey = card.get("journey")
    if journey not in JOURNEYS:
        journey = "cross-journey"
    return {
        "id": _doc_id_card(str(card.get("id") or "untitled")),
        "type": "brd",
        "title": card.get("title") or str(card.get("id") or "untitled"),
        "status": status,
        "journey": journey,
        "brands": brands,
        "link": card.get("path") or "",
    }


def decide_run(run_id: str, runs_dir: Path, inventory: dict) -> tuple[int, dict, dict, list[dict]]:
    if not is_approved(run_id, runs_dir):
        return 1, {}, inventory, [_fail("missing_approved", "APPROVED", "APPROVED missing or stale")]
    try:
        answers = read_json(run_id, "answers.json", runs_dir)
    except FileNotFoundError:
        return 2, {}, inventory, [_fail("missing_file", "answers.json", "answers.json missing")]
    failures = validate_answers(answers)
    if failures:
        return 1, {}, inventory, failures

    action = answers["doc_action"]
    rec_id = (answers.get("recommendation") or {}).get("option_id")
    writes: list[dict] = []
    updated = copy.deepcopy(inventory)

    if action == "new" and not _is_do_nothing(answers):
        doc_id = _doc_id_run(run_id)
        _upsert_doc(updated, _doc_from_answers(answers, doc_id, "approved"))
        writes.append({"op": "upsert_doc", "id": doc_id})
    elif action == "amend":
        target = answers.get("amend_target_id")
        if not target:
            return 1, {}, inventory, [_fail("missing_target", "amend_target_id", "amend needs amend_target_id")]
        if not _find_doc(updated, target):
            return 1, {}, inventory, [_fail("missing_target", "amend_target_id", f"unknown doc {target}")]
        _upsert_doc(updated, _doc_from_answers(answers, target, "approved"))
        writes.append({"op": "upsert_doc", "id": target})
    elif action == "kill":
        target = answers.get("amend_target_id")
        if not target:
            return 1, {}, inventory, [_fail("missing_target", "amend_target_id", "kill needs amend_target_id")]
        if not _kill_doc(updated, target):
            return 1, {}, inventory, [_fail("missing_target", "amend_target_id", f"unknown doc {target}")]
        writes.append({"op": "kill_doc", "id": target})
    else:
        writes.append({"op": "none", "id": None})

    decision = {
        "id": f"dec-{slugify(run_id)}",
        "source": "run",
        "locked": {
            "kind": "option",
            "option_id": rec_id,
            "doc_action": action,
            "amend_target_id": answers.get("amend_target_id"),
            "title": answers["title"],
            "decision": answers["decision"],
            "brands": expand_brands(answers.get("brands") or []),
            "journey": answers["journey"],
        },
        "inventory_writes": writes,
    }
    return 0, decision, updated, []


def decide_triage(folder: Path, inventory: dict) -> tuple[int, dict, dict, list[dict]]:
    path = folder / "triage.json"
    if not path.is_file():
        return 2, {}, inventory, [_fail("missing_file", str(path), "triage.json missing")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 2, {}, inventory, [_fail("unreadable_file", str(path), str(exc))]
    if not isinstance(payload, dict):
        return 1, {}, inventory, [_fail("bad_type", str(path), "triage.json must be an object")]

    cards = [c for c in (payload.get("cards") or []) if isinstance(c, dict)]
    clusters = [c for c in (payload.get("clusters") or []) if isinstance(c, dict)]
    by_id = {c.get("id"): c for c in cards}
    loser_ids: set[str] = set()
    survivor_ids: set[str] = set()
    for cluster in clusters:
        survivor = cluster.get("survivor")
        members = cluster.get("members") or []
        if survivor:
            survivor_ids.add(survivor)
        for mid in members:
            if mid != survivor:
                loser_ids.add(mid)

    writes: list[dict] = []
    updated = copy.deepcopy(inventory)

    for sid in survivor_ids:
        card = by_id.get(sid)
        if not card or "already-ships" in (card.get("reasons") or []):
            continue
        doc = _card_doc(card, "open")
        if not doc:
            continue
        _upsert_doc(updated, doc)
        writes.append({"op": "upsert_doc", "id": doc["id"]})

    for lid in loser_ids:
        doc_id = _doc_id_card(str(lid))
        if _kill_doc(updated, doc_id):
            writes.append({"op": "kill_doc", "id": doc_id})

    for card in cards:
        cid = card.get("id")
        if cid in survivor_ids or cid in loser_ids:
            continue
        labels = card.get("labels") or []
        if "high-priority" in labels and "deprioritise" not in labels:
            doc = _card_doc(card, "open")
            if not doc:
                continue
            _upsert_doc(updated, doc)
            writes.append({"op": "upsert_doc", "id": doc["id"]})

    if not writes:
        writes.append({"op": "none", "id": None})

    decision = {
        "id": f"dec-triage-{slugify(folder.name)}",
        "source": "triage",
        "locked": {
            "kind": "labels",
            "cards": [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "labels": c.get("labels") or [],
                    "cluster_id": c.get("cluster_id"),
                }
                for c in cards
            ],
            "clusters": [
                {"id": cl.get("id"), "survivor": cl.get("survivor"), "members": cl.get("members") or []}
                for cl in clusters
            ],
        },
        "inventory_writes": writes,
    }
    return 0, decision, updated, []
