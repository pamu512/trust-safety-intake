from __future__ import annotations

import re

from trust_intake.answers import NEEDED_SLOTS
from trust_intake.ledger import build_ledger

RANGES = {
    "run-rate": 0.20,
    "share-of-parent": 0.25,
    "last-period-carry": 0.30,
    "peer-brand-ratio": 0.35,
}

COLUMN_TO_SLOT = (
    (("loss", "euro", "eur"), "euro_impact"),
    (("volume", "claim"), "volume"),
    (("rate", "pct", "fp", "fp_rate", "false_positive"), "rate"),
)
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _ledger_map(answers: dict, facts: dict) -> dict[str, dict]:
    rows = build_ledger(facts, answers, {"estimates": []})
    return {r["name"]: r for r in rows}


def _range(value: float, method: str) -> dict:
    delta = RANGES[method]
    return {"low": value * (1 - delta), "high": value * (1 + delta)}


def _estimate(name: str, value: float, unit: str | None, method: str, inputs: list[str]) -> dict:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "source": "ESTIMATE",
        "method": method,
        "inputs": inputs,
        "range": _range(value, method),
    }


def _has_alias(col: str, keys: tuple[str, ...]) -> bool:
    low = col.lower()
    tokens = {t for t in _TOKEN_RE.split(low) if t}
    padded = f"_{low}_"
    for key in keys:
        if low == key or key in tokens or f"_{key}_" in padded:
            return True
    return False


def _slot_from_column(col: str) -> str | None:
    low = col.lower()
    for keys, slot in COLUMN_TO_SLOT:
        if slot == "rate":
            if _has_alias(low, keys):
                return slot
        elif any(k in low for k in keys):
            return slot
    return None


def extrapolate(answers: dict, facts: dict) -> dict:
    ledger = _ledger_map(answers, facts)
    estimates: list[dict] = []
    unknown: list[str] = []
    elapsed = answers.get("elapsed_fraction")
    shares = answers.get("shares") or {}
    brands = answers.get("brands") or []
    for slot in NEEDED_SLOTS:
        metric = (answers.get("needed_metrics") or {}).get(slot) or {}
        if metric.get("value") is not None:
            continue
        unit = metric.get("unit")
        partial = ledger.get(f"partial_{slot}")
        if partial and elapsed and 0 < float(elapsed) <= 1:
            value = float(partial["value"]) / float(elapsed)
            estimates.append(_estimate(slot, value, unit or partial.get("unit"), "run-rate", [partial["name"], "elapsed_fraction"]))
            continue
        parent = ledger.get(f"parent_{slot}")
        share = shares.get(slot)
        if parent and share and 0 < float(share) <= 1:
            value = float(parent["value"]) * float(share)
            estimates.append(_estimate(slot, value, unit or parent.get("unit"), "share-of-parent", [parent["name"], f"shares.{slot}"]))
            continue
        carried = None
        for table in facts.get("tables") or []:
            series = table.get("series") or []
            if not series:
                continue
            last = series[-1]["values"]
            for col, val in last.items():
                if _slot_from_column(col) == slot:
                    carried = (f"{table['name']}.{col}", val, unit)
        if carried:
            estimates.append(_estimate(slot, float(carried[1]), carried[2], "last-period-carry", [carried[0]]))
            continue
        peer_done = False
        for brand in brands:
            for name, row in ledger.items():
                if name == f"{slot}_{brand}":
                    continue
                prefix = f"{slot}_"
                if not name.startswith(prefix):
                    continue
                peer = name[len(prefix) :]
                gmv_a = ledger.get(f"gmv_{brand}")
                gmv_p = ledger.get(f"gmv_{peer}")
                if gmv_a and gmv_p and float(gmv_p["value"]):
                    value = float(row["value"]) * float(gmv_a["value"]) / float(gmv_p["value"])
                    estimates.append(_estimate(slot, value, unit, "peer-brand-ratio", [name, gmv_a["name"], gmv_p["name"]]))
                    peer_done = True
                    break
            if peer_done:
                break
        if peer_done:
            continue
        unknown.append(slot)
    return {"estimates": estimates, "unknown": unknown}
