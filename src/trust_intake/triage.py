from __future__ import annotations

import difflib
from pathlib import Path

from trust_intake.match_inventory import THRESHOLD, score_overlap
from trust_intake.triage_extract import extract_card
from trust_intake.triage_read import read_document, read_sidecar

_SKIP_NAMES = {"triage.json", "triage.md"}
_DEPRIOR_REASONS = ("thin", "already-ships", "no-numbers")


def _known_journey(journey: str | None) -> bool:
    return bool(journey) and journey != "unknown"


def _brand_jaccard(a: list[str] | None, b: list[str] | None) -> float:
    left, right = set(a or []), set(b or [])
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def score_pair(a: dict, b: dict) -> float:
    if _known_journey(a.get("journey")) and _known_journey(b.get("journey")):
        return score_overlap(
            a["title"],
            a["journey"],
            a.get("brands") or [],
            {"title": b["title"], "journey": b["journey"], "brands": b.get("brands") or []},
        )
    title_a = (a.get("title") or "").lower()
    title_b = (b.get("title") or "").lower()
    return 0.5 * _brand_jaccard(a.get("brands"), b.get("brands")) + 0.5 * difflib.SequenceMatcher(
        None, title_a, title_b
    ).ratio()


def _metric_missing(metric: dict | None) -> bool:
    if not metric:
        return True
    return metric.get("value") is None or metric.get("source") == "missing"


def _euro_value(card: dict) -> float | None:
    return (card.get("euro_impact") or {}).get("value")


def _format_euro(card: dict) -> str:
    euro = card.get("euro_impact") or {}
    value = euro.get("value")
    source = euro.get("source") or "missing"
    if value is None or source == "missing":
        text = "€ missing"
    else:
        shown = int(value) if isinstance(value, (int, float)) and float(value) == int(value) else value
        text = f"€{shown} ({source})"
    if euro.get("estimate"):
        text = f"{text} ESTIMATE"
    return text


def _inventory_overlaps(card: dict, inventory: dict) -> list[dict]:
    overlaps = []
    for kind, rows in (("control", inventory.get("controls") or []), ("doc", inventory.get("docs") or [])):
        for item in rows:
            item_card = {
                "title": item.get("title") or item.get("name") or "",
                "journey": item.get("journey"),
                "brands": item.get("brands") or [],
            }
            score = score_pair(card, item_card)
            if score >= THRESHOLD:
                overlaps.append(
                    {
                        "id": item.get("id"),
                        "kind": kind,
                        "title": item_card["title"],
                        "score": round(score, 4),
                    }
                )
    overlaps.sort(key=lambda o: o["score"], reverse=True)
    return overlaps


def _survivor(cards: list[dict]) -> dict:
    def key(card: dict) -> tuple[float, int]:
        euro = _euro_value(card)
        spread = len(card.get("brands") or []) + len(card.get("markets") or [])
        return (euro if euro is not None else -1, spread)

    return max(cards, key=key)


def cluster_unify(cards: list[dict]) -> list[dict]:
    n = len(cards)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if score_pair(cards[i], cards[j]) >= THRESHOLD:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        members = [cards[i] for i in idxs]
        cluster_id = f"cluster-{_survivor(members)['id']}"
        for card in members:
            card["cluster_id"] = cluster_id
            labels = card.setdefault("labels", [])
            if "unify" not in labels:
                labels.append("unify")
    return cards


def label_cards(cards: list[dict], inventory: dict, min_euro: float) -> list[dict]:
    for card in cards:
        labels = card.setdefault("labels", [])
        reasons = card.setdefault("reasons", [])
        brands = card.get("brands") or []
        markets = card.get("markets") or []
        scored_overlaps = _inventory_overlaps(card, inventory)
        card["inventory_overlaps"] = scored_overlaps

        if not brands and not markets:
            if "extraction-gap" not in labels:
                labels.append("extraction-gap")
            if "extraction-gap" not in reasons:
                reasons.append("extraction-gap")

        if len(brands) >= 2 or len(markets) >= 2:
            if "high-priority" not in labels:
                labels.append("high-priority")

        deprior: list[str] = []
        euro = card.get("euro_impact") or {}
        if len(brands) == 1 and len(markets) == 1 and (_metric_missing(euro) or (euro.get("value") or 0) < min_euro):
            deprior.append("thin")
        if scored_overlaps:
            deprior.append("already-ships")
        if (
            _metric_missing(card.get("euro_impact"))
            and _metric_missing(card.get("volume"))
            and _metric_missing(card.get("rate"))
        ):
            deprior.append("no-numbers")

        for reason in deprior:
            if reason not in reasons:
                reasons.append(reason)
        if deprior and "deprioritise" not in labels:
            labels.append("deprioritise")
    return cards


def _build_clusters(cards: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for card in cards:
        cid = card.get("cluster_id")
        if cid:
            grouped.setdefault(cid, []).append(card)
    clusters = []
    for cid, members in grouped.items():
        if len(members) < 2:
            continue
        pairwise = []
        for i, left in enumerate(members):
            for right in members[i + 1 :]:
                pairwise.append({"a": left["id"], "b": right["id"], "score": round(score_pair(left, right), 4)})
        clusters.append(
            {
                "id": cid,
                "members": [c["id"] for c in members],
                "survivor": _survivor(members)["id"],
                "pairwise": pairwise,
                "markets": sorted({m for c in members for m in (c.get("markets") or [])}),
            }
        )
    return clusters


def render_triage_md(payload: dict) -> str:
    cards = payload.get("cards") or []
    clusters = payload.get("clusters") or []
    warnings = payload.get("warnings") or []
    high = [c for c in cards if "high-priority" in (c.get("labels") or [])]
    high.sort(
        key=lambda c: (
            -len(c.get("brands") or []),
            -len(c.get("markets") or []),
            -(_euro_value(c) if _euro_value(c) is not None else -1),
        )
    )
    lines = ["# BRD triage", "", "## High priority", ""]
    if not high:
        lines.append("(none)")
    else:
        for card in high:
            lines.append(
                f"- {card['id']}: {card.get('title')} brands={card.get('brands')} markets={card.get('markets')} {_format_euro(card)}"
            )
    lines += ["", "## Unify", ""]
    if not clusters:
        lines.append("(none)")
    else:
        by_id = {c["id"]: c for c in cards}
        for cluster in clusters:
            lines.append(f"### {cluster['id']}")
            member_bits = [f"{mid} {_format_euro(by_id.get(mid, {}))}" for mid in cluster["members"]]
            lines.append(f"- members: {', '.join(member_bits)}")
            survivor = cluster["survivor"]
            lines.append(f"- survivor: {survivor} {_format_euro(by_id.get(survivor, {}))}")
            lines.append(f"- markets: {', '.join(cluster.get('markets') or [])}")
            for pair in cluster.get("pairwise") or []:
                lines.append(f"- score {pair['a']}–{pair['b']}: {pair['score']}")
            lines.append("")
    lines += ["## Deprioritise", ""]
    deprior = [c for c in cards if "deprioritise" in (c.get("labels") or [])]
    if not deprior:
        lines.append("(none)")
    else:
        by_reason: dict[str, list[dict]] = {r: [] for r in _DEPRIOR_REASONS}
        for card in deprior:
            for reason in card.get("reasons") or []:
                if reason in by_reason:
                    by_reason[reason].append(card)
        for reason in _DEPRIOR_REASONS:
            rows = by_reason[reason]
            if not rows:
                continue
            lines.append(f"### {reason}")
            for card in rows:
                lines.append(f"- {card['id']}: {card.get('title')} {_format_euro(card)}")
            lines.append("")
    lines += ["## Extraction gaps", ""]
    gaps = [c for c in cards if "extraction-gap" in (c.get("labels") or [])]
    if not gaps:
        lines.append("(none)")
    else:
        for card in gaps:
            lines.append(f"- {card['id']}: {card.get('path')}")
    lines += ["", "## Warnings", ""]
    if not warnings:
        lines.append("(none)")
    else:
        for warning in warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def run_triage(folder: Path, inventory: dict, markets: dict, min_euro: float) -> tuple[int, dict]:
    payload: dict = {"cards": [], "clusters": [], "warnings": [], "min_euro": min_euro}
    if not folder.is_dir():
        payload["warnings"].append(f"missing folder: {folder}")
        return 2, payload
    cards: list[dict] = []
    try:
        paths = sorted(p for p in folder.iterdir() if p.is_file())
    except OSError as exc:
        payload["warnings"].append(f"unreadable folder: {exc}")
        return 2, payload
    for path in paths:
        if path.name in _SKIP_NAMES or path.name.endswith(".meta.json"):
            continue
        try:
            text = read_document(path)
        except ValueError as exc:
            if str(exc) == "unsupported":
                payload["warnings"].append(f"unsupported: {path.name}")
            else:
                payload["warnings"].append(f"unreadable: {path.name}: {exc}")
            continue
        except OSError as exc:
            payload["warnings"].append(f"unreadable: {path.name}: {exc}")
            continue
        try:
            sidecar = read_sidecar(path)
        except (OSError, ValueError) as exc:
            payload["warnings"].append(f"sidecar: {path.name}: {exc}")
            sidecar = {}
        for key in ("brands", "markets"):
            if key in sidecar and not isinstance(sidecar[key], (list, str)):
                payload["warnings"].append(f"sidecar: {path.name}: {key} must be a list or string")
        cards.append(extract_card(path, text, sidecar, markets))
    if not cards:
        return 1, payload
    label_cards(cards, inventory, min_euro)
    cluster_unify(cards)
    payload["cards"] = cards
    payload["clusters"] = _build_clusters(cards)
    return 0, payload
