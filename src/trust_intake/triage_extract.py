from __future__ import annotations

import re
from pathlib import Path

from trust_intake.answers import BRANDS, JOURNEYS
from trust_intake.ledger import scan_quantities
from trust_intake.markets import resolve_markets

_VOLUME_UNITS = ("orders", "claims", "flags", "payouts")
_ALL_BRANDS_RE = re.compile(r"\ball(?: three)? brands\b", re.I)
_HEADING_RE = re.compile(r"^#\s+(.*)")


def extract_card(path: Path, text: str, sidecar: dict, markets: dict) -> dict:
    euro, rate, volume, volume_unit = _quantities(text)
    return {
        "id": path.stem,
        "path": str(path),
        "title": _title(path, text),
        "brands": sidecar["brands"] if "brands" in sidecar else _brands(text),
        "markets": sidecar["markets"] if "markets" in sidecar else resolve_markets(text, markets),
        "journey": sidecar["journey"] if "journey" in sidecar else _journey(text),
        "euro_impact": _metric(sidecar, "euro_impact", euro, "EUR"),
        "volume": _metric(sidecar, "volume", volume, volume_unit),
        "rate": _metric(sidecar, "rate", rate, "%"),
    }


def _title(path: Path, text: str) -> str:
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            return match.group(1).strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return path.stem


def _brands(text: str) -> list[str]:
    if _ALL_BRANDS_RE.search(text):
        return list(BRANDS)
    return [brand for brand in BRANDS if re.search(rf"\b{re.escape(brand)}\b", text, flags=re.I)]


def _journey(text: str) -> str:
    hits: list[str] = []
    for token in JOURNEYS:
        if re.search(rf"\b{re.escape(token)}\b", text, flags=re.I):
            hits.append(token)
    if "claims-cancel" not in hits:
        if re.search(r"\bclaims\b", text, flags=re.I) and re.search(r"\bcancel\b", text, flags=re.I):
            hits.append("claims-cancel")
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return "cross-journey"
    return "unknown"


def _quantities(text: str) -> tuple[float | None, float | None, float | None, str | None]:
    euro = rate = volume = None
    volume_unit = None
    for token, value in scan_quantities(text):
        upper = token.upper()
        if euro is None and ("€" in token or "EUR" in upper):
            euro = value
        elif rate is None and "%" in token:
            rate = value
        elif volume is None:
            unit_match = re.search("|".join(_VOLUME_UNITS), token, flags=re.I)
            if unit_match:
                volume = value
                volume_unit = unit_match.group(0).lower()
    return euro, rate, volume, volume_unit


def _metric(sidecar: dict, key: str, value: float | None, unit: str | None) -> dict:
    if key in sidecar:
        raw = sidecar[key]
        if isinstance(raw, dict):
            return {
                "value": raw.get("value"),
                "unit": raw.get("unit", unit),
                "source": "sidecar",
            }
        return {"value": raw, "unit": unit, "source": "sidecar"}
    if value is not None:
        return {"value": value, "unit": unit, "source": "extract"}
    return {"value": None, "unit": unit, "source": "missing"}
