from __future__ import annotations

import re

UNIT_WORDS = ("orders", "GMV", "bps", "FTE", "flags", "claims", "payouts")
EUR_RE = re.compile(r"(?:€|EUR)\s*([\d,]+(?:\.\d+)?)([kKmMbB])?", re.I)
PCT_RE = re.compile(r"(?<![\d-])(\d+(?:\.\d+)?)%")
UNIT_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s+(" + "|".join(UNIT_WORDS) + r")\b")
SKIP_RE = re.compile(r"90[- ]day", re.I)


def _suffix(mult: str | None) -> float:
    if not mult:
        return 1.0
    return {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[mult.lower()]


def build_ledger(facts: dict, answers: dict, estimates: dict) -> list[dict]:
    rows: list[dict] = []
    for item in facts.get("derived") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "csv"})
    for item in answers.get("numbers_from_author") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "interview"})
    for item in (estimates or {}).get("estimates") or []:
        rows.append({"name": item["name"], "value": item["value"], "unit": item.get("unit"), "source": "ESTIMATE"})
    return rows


def scan_quantities(text: str) -> list[tuple[str, float]]:
    if SKIP_RE.search(text):
        text_for_pct = SKIP_RE.sub(" ", text)
    else:
        text_for_pct = text
    found: list[tuple[str, float]] = []
    for m in EUR_RE.finditer(text):
        found.append((m.group(0).strip(), float(m.group(1).replace(",", "")) * _suffix(m.group(2))))
    for m in PCT_RE.finditer(text_for_pct):
        found.append((m.group(0), float(m.group(1)) / 100.0))
    for m in UNIT_RE.finditer(text):
        found.append((m.group(0), float(m.group(1).replace(",", ""))))
    return found


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 * max(1.0, abs(b))


def unresolved_quantities(text: str, ledger: list[dict]) -> list[str]:
    values = [float(r["value"]) for r in ledger]
    leftover = []
    for token, val in scan_quantities(text):
        if not any(_close(val, lv) for lv in values):
            leftover.append(token)
    return leftover
