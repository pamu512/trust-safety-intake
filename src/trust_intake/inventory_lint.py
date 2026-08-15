from __future__ import annotations

from pathlib import Path

import yaml

from trust_intake.answers import BRANDS, JOURNEYS

CONTROL_TYPES = ("rule", "ml", "policy", "ops")
CONTROL_STATUS = ("live", "pilot", "planned", "retired")
DOC_TYPES = ("brd", "prd", "business-case", "case-study", "ticket")
DOC_STATUS = ("draft", "open", "approved", "shipped", "killed")


def load_inventory(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("inventory must be a mapping")
    return data


def save_inventory(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def lint_inventory(data: dict) -> list[dict]:
    fails: list[dict] = []
    for key in ("brands", "journeys", "stack", "controls", "docs"):
        if key not in data:
            fails.append({"code": "missing_key", "path": key, "message": f"missing {key}"})
    if fails:
        return fails
    if list(data["brands"]) != list(BRANDS):
        fails.append({"code": "bad_brands", "path": "brands", "message": "brands must be the three Pandora brands"})
    if list(data["journeys"]) != list(JOURNEYS):
        fails.append({"code": "bad_journeys", "path": "journeys", "message": "journeys enum mismatch"})
    ids: dict[str, str] = {}
    for group in ("stack", "controls", "docs"):
        for i, row in enumerate(data[group] or []):
            rid = row.get("id")
            path = f"{group}[{i}]"
            if not rid:
                fails.append({"code": "missing_id", "path": path, "message": "id required"})
                continue
            if rid in ids:
                fails.append({"code": "duplicate_id", "path": path, "message": f"duplicate id {rid}"})
            ids[rid] = group
    doc_ids = {d.get("id") for d in data["docs"] or []}
    for i, ctl in enumerate(data["controls"] or []):
        if ctl.get("type") not in CONTROL_TYPES:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].type", "message": "bad type"})
        if ctl.get("status") not in CONTROL_STATUS:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].status", "message": "bad status"})
        if ctl.get("journey") not in JOURNEYS:
            fails.append({"code": "bad_enum", "path": f"controls[{i}].journey", "message": "bad journey"})
        for ref in ctl.get("related_docs") or []:
            if ref not in doc_ids:
                fails.append({"code": "dangling_related_docs", "path": f"controls[{i}].related_docs", "message": ref})
    for i, doc in enumerate(data["docs"] or []):
        if doc.get("type") not in DOC_TYPES:
            fails.append({"code": "bad_enum", "path": f"docs[{i}].type", "message": "bad type"})
        if doc.get("status") not in DOC_STATUS:
            fails.append({"code": "bad_enum", "path": f"docs[{i}].status", "message": "bad status"})
    return fails
