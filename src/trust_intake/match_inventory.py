from __future__ import annotations

import re

from trust_intake.answers import expand_brands

THRESHOLD = 0.72
# ponytail: char-ratio matched unrelated titles once journey+brand hit 0.70. Token Jaccard + floor; upgrade to shared IDs when inventory has them.
TITLE_FLOOR = 0.3
_STOP = {"the", "a", "an", "for", "and", "or", "of", "to", "in", "on", "with"}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _title(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "")


def title_tokens(title: str) -> set[str]:
    return {w for w in _TOKEN_RE.findall(title.lower()) if w not in _STOP and len(w) > 1}


def title_jaccard(left: str, right: str) -> float:
    a, b = title_tokens(left), title_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_overlap(title: str, journey: str, brands: list[str], item: dict) -> float:
    title_score = title_jaccard(title, _title(item))
    if title_score < TITLE_FLOOR:
        return 0.0
    journey_score = 1.0 if item.get("journey") == journey else 0.0
    item_brands = set(item.get("brands") or [])
    author_brands = set(expand_brands(brands))
    if not item_brands or not author_brands:
        brand_score = 0.0
    else:
        brand_score = len(item_brands & author_brands) / len(item_brands | author_brands)
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
