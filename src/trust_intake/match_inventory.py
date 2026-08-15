from __future__ import annotations

import difflib

from trust_intake.answers import expand_brands

THRESHOLD = 0.72


def _title(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "")


def score_overlap(title: str, journey: str, brands: list[str], item: dict) -> float:
    journey_score = 1.0 if item.get("journey") == journey else 0.0
    item_brands = set(item.get("brands") or [])
    author_brands = set(expand_brands(brands))
    if not item_brands or not author_brands:
        brand_score = 0.0
    else:
        brand_score = len(item_brands & author_brands) / len(item_brands | author_brands)
    title_score = difflib.SequenceMatcher(None, title.lower(), _title(item).lower()).ratio()
    return 0.4 * journey_score + 0.3 * brand_score + 0.3 * title_score


def match(answers: dict, inventory: dict) -> dict:
    title = answers["title"]
    journey = answers["journey"]
    brands = answers.get("brands") or []
    overlaps = []
    for kind, rows in (("control", inventory.get("controls") or []), ("doc", inventory.get("docs") or [])):
        for item in rows:
            s = score_overlap(title, journey, brands, item)
            overlaps.append(
                {
                    "id": item.get("id"),
                    "kind": kind,
                    "title": _title(item),
                    "score": round(s, 4),
                }
            )
    overlaps.sort(key=lambda o: o["score"], reverse=True)
    return {
        "threshold": THRESHOLD,
        "overlaps": [o for o in overlaps if o["score"] >= THRESHOLD],
        "scored": overlaps,
    }
