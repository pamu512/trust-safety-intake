from __future__ import annotations

import re
from pathlib import Path

from trust_intake.answers import BRANDS, JOURNEYS, expand_brands
from trust_intake.ledger import scan_quantities
from trust_intake.markets import resolve_markets

_VOLUME_UNITS = ("orders", "claims", "flags", "payouts")
_ALL_BRANDS_RE = re.compile(r"\ball(?: three)? brands\b", re.I)
_HEADING_RE = re.compile(r"^#\s+(.*)")
_ESTIMATE_RE = re.compile(r"estimate|approx|~", re.I)
_JOURNEY_LABEL_RE = re.compile(r"^\s*journey\s*:", re.I)


def _as_str_list(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError("expected list or string")


def extract_card(path: Path, text: str, sidecar: dict, markets: dict) -> dict:
    euro, rate, volume, volume_unit, euro_est, rate_est, volume_est = _quantities(text)
    try:
        brands = expand_brands(_as_str_list(sidecar["brands"])) if "brands" in sidecar else _brands(text)
    except (TypeError, ValueError):
        brands = _brands(text)
    try:
        card_markets = _as_str_list(sidecar["markets"]) if "markets" in sidecar else resolve_markets(text, markets)
    except (TypeError, ValueError):
        card_markets = resolve_markets(text, markets)
    return {
        "id": path.stem,
        "path": str(path),
        "title": _title(path, text),
        "brands": brands,
        "markets": card_markets,
        "journey": sidecar["journey"] if "journey" in sidecar else _journey(text),
        "euro_impact": _metric(sidecar, "euro_impact", euro, "EUR", euro_est),
        "volume": _metric(sidecar, "volume", volume, volume_unit, volume_est),
        "rate": _metric(sidecar, "rate", rate, "%", rate_est),
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
        if token == "account":
            continue
        if re.search(rf"\b{re.escape(token)}\b", text, flags=re.I):
            hits.append(token)
    if "account" not in hits:
        for line in text.splitlines():
            if _JOURNEY_LABEL_RE.match(line) and re.search(r"\baccount\b", line, flags=re.I):
                hits.append("account")
                break
    if "claims-cancel" not in hits:
        if re.search(r"\bclaims\b", text, flags=re.I) and re.search(r"\bcancel\b", text, flags=re.I):
            hits.append("claims-cancel")
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return "cross-journey"
    return "unknown"


def _line_for_token(text: str, token: str) -> str:
    for line in text.splitlines():
        if token in line:
            return line
    return ""


def _quantities(text: str) -> tuple[float | None, float | None, float | None, str | None, bool, bool, bool]:
    euro = rate = volume = None
    volume_unit = None
    euro_est = rate_est = volume_est = False
    for token, value in scan_quantities(text):
        upper = token.upper()
        estimate = bool(_ESTIMATE_RE.search(_line_for_token(text, token)))
        if euro is None and ("€" in token or "EUR" in upper):
            euro = value
            euro_est = estimate
        elif rate is None and "%" in token:
            rate = value * 100.0
            rate_est = estimate
        elif volume is None:
            unit_match = re.search("|".join(_VOLUME_UNITS), token, flags=re.I)
            if unit_match:
                volume = value
                volume_unit = unit_match.group(0).lower()
                volume_est = estimate
    return euro, rate, volume, volume_unit, euro_est, rate_est, volume_est


def _metric(sidecar: dict, key: str, value: float | None, unit: str | None, estimate: bool = False) -> dict:
    if key in sidecar:
        raw = sidecar[key]
        if isinstance(raw, dict):
            out = {
                "value": raw.get("value"),
                "unit": raw.get("unit", unit),
                "source": "sidecar",
            }
            if raw.get("estimate"):
                out["estimate"] = True
            return out
        return {"value": raw, "unit": unit, "source": "sidecar"}
    if value is not None:
        out = {"value": value, "unit": unit, "source": "extract"}
        if estimate:
            out["estimate"] = True
        return out
    return {"value": None, "unit": unit, "source": "missing"}
