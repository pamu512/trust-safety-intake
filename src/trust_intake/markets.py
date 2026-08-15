from __future__ import annotations

import re
from pathlib import Path

import yaml


def load_markets(path: Path) -> dict[str, list[str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    fails = lint_markets(raw if isinstance(raw, dict) else {})
    if fails:
        raise ValueError(fails)
    out: dict[str, list[str]] = {}
    for row in raw["markets"]:
        aliases = [row["id"], *(row.get("aliases") or [])]
        out[row["id"]] = aliases
    return out


def lint_markets(data: dict) -> list[dict]:
    fails = []
    if "markets" not in data:
        return [{"code": "missing_key", "path": "markets", "message": "missing markets"}]
    seen = set()
    for i, row in enumerate(data["markets"] or []):
        rid = (row or {}).get("id")
        if not rid:
            fails.append({"code": "missing_id", "path": f"markets[{i}]", "message": "id required"})
            continue
        if rid in seen:
            fails.append({"code": "duplicate_id", "path": f"markets[{i}]", "message": rid})
        seen.add(rid)
    return fails


def resolve_markets(text: str, markets: dict[str, list[str]]) -> list[str]:
    found = set()
    for mid, aliases in markets.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.I):
                found.add(mid)
                break
    return sorted(found)
