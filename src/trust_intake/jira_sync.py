from __future__ import annotations

import base64
import copy
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from trust_intake.answers import BRANDS, JOURNEYS, expand_brands
from trust_intake.inventory_lint import lint_inventory
from trust_intake.run_store import slugify

DOC_PREFIX_DEFAULT = "doc-jira-"
CTL_PREFIX_DEFAULT = "ctl-jira-"


def _fail(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def load_jira_config(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("jira config must be a mapping")
    return raw


def _status_name(raw) -> str:
    if isinstance(raw, dict):
        return str(raw.get("name") or "")
    return str(raw or "")


def normalize_issue(raw: dict, browse_base: str) -> dict:
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    key = str(raw.get("key") or "").strip()
    title = str(raw.get("title") or raw.get("summary") or fields.get("summary") or "").strip()
    status = _status_name(raw.get("status") or fields.get("status"))
    labels = raw.get("labels") if raw.get("labels") is not None else fields.get("labels") or []
    if not isinstance(labels, list):
        labels = [str(labels)]
    labels = [str(x) for x in labels]
    url = str(raw.get("url") or raw.get("self") or "").strip()
    if (not url or "/rest/" in url) and key and browse_base:
        url = f"{browse_base.rstrip('/')}/browse/{key}"
    return {"key": key, "title": title, "status": status, "labels": labels, "url": url}


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _alias_lookup(raw: dict, enums: tuple[str, ...], prefix: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for enum in enums:
        lookup[enum.lower()] = enum
        lookup[f"{prefix}{enum}".lower()] = enum
    for enum, aliases in (raw or {}).items():
        if enum not in enums:
            continue
        lookup[str(enum).lower()] = enum
        for alias in _as_list(aliases):
            token = alias.strip().lower()
            if token:
                lookup[token] = enum
                lookup[token.removeprefix(prefix)] = enum
    return lookup


def _journey(labels: list[str], config: dict, default: str | None) -> str | None:
    lookup = _alias_lookup(config.get("journey_labels") or {}, JOURNEYS, "journey-")
    for lab in labels:
        token = str(lab).strip().lower()
        if token in lookup:
            return lookup[token]
        stripped = token.removeprefix("journey-")
        if stripped in lookup:
            return lookup[stripped]
    return default if default in JOURNEYS else None


_BRAND_SLOT_RE = re.compile(r"brand[\s_-]*(\d+)$", re.I)


def _brand_enum(key: str) -> str | None:
    if key in BRANDS:
        return key
    match = _BRAND_SLOT_RE.match(str(key).strip())
    if not match:
        return None
    index = int(match.group(1))
    if 1 <= index <= len(BRANDS):
        return BRANDS[index - 1]
    return None


def _brand_lookup(config: dict) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for i, enum in enumerate(BRANDS, start=1):
        for alias in (f"brand {i}", f"brand-{i}", f"brand{i}"):
            lookup[alias] = enum
    for key, aliases in (config.get("brand_labels") or {}).items():
        enum = _brand_enum(str(key))
        if not enum:
            continue
        for alias in _as_list(aliases):
            token = alias.strip().lower()
            if token:
                lookup[token] = enum
    return lookup


def _brands(labels: list[str], config: dict, default: list[str]) -> list[str]:
    lookup = _brand_lookup(config)
    found = []
    for lab in labels:
        token = str(lab).strip().lower()
        enum = lookup.get(token)
        if enum and enum not in found:
            found.append(enum)
    if found:
        return found
    return expand_brands(default)


def _control_labels(config: dict) -> set[str]:
    names = _as_list(config.get("control_labels"))
    if not names:
        names = _as_list(config.get("control_label") or "capability")
    return {n.strip().lower() for n in names if n and str(n).strip()}


def _prefixed_id(prefix: str, slug: str) -> str:
    p = str(prefix)
    return f"{p}{slug}" if p.endswith("-") else f"{p}-{slug}"


def _map_status(name: str, table: dict, fallback: str) -> str:
    if name in table:
        return str(table[name])
    for key, val in table.items():
        if str(key).lower() == name.lower():
            return str(val)
    return fallback


def map_issue(issue: dict, config: dict) -> dict | None:
    key = issue.get("key") or ""
    title = issue.get("title") or ""
    if not key or not title:
        return None
    labels = issue.get("labels") or []
    defaults = config.get("defaults") or {}
    journey = _journey(labels, config, None)
    brands = _brands(labels, config, defaults.get("brands") or [])
    if not journey and not brands:
        return None
    if not journey:
        journey = defaults.get("journey") if defaults.get("journey") in JOURNEYS else "cross-journey"
    if not brands:
        return None
    slug = slugify(key)
    doc_id = _prefixed_id(config.get("id_prefix") or DOC_PREFIX_DEFAULT, slug)
    ctl_id = _prefixed_id(config.get("control_prefix") or CTL_PREFIX_DEFAULT, slug)
    status_docs = config.get("status_docs") or {}
    status_controls = config.get("status_controls") or {}
    doc = {
        "id": doc_id,
        "type": "ticket",
        "title": title,
        "status": _map_status(issue.get("status") or "", status_docs, "open"),
        "journey": journey,
        "brands": brands,
        "link": issue.get("url") or "",
    }
    control = None
    if _control_labels(config) & {str(lab).strip().lower() for lab in labels}:
        ctl_type = config.get("default_control_type") or "ops"
        control = {
            "id": ctl_id,
            "name": title,
            "type": ctl_type if ctl_type in ("rule", "ml", "policy", "ops") else "ops",
            "journey": journey,
            "brands": brands,
            "status": _map_status(issue.get("status") or "", status_controls, "planned"),
            "owner": config.get("default_owner") or "jira",
            "related_docs": [doc_id],
        }
    return {"doc": doc, "control": control, "key": key}


def load_issues_json(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("issues") or []
    else:
        raise ValueError("json must be a list or {issues: []}")
    if not isinstance(rows, list):
        raise ValueError("issues must be a list")
    return [row for row in rows if isinstance(row, dict)]


def fetch_issues_jira(config: dict) -> list[dict]:
    base = (os.environ.get("JIRA_BASE_URL") or "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL") or ""
    token = os.environ.get("JIRA_API_TOKEN") or ""
    if not base or not email or not token:
        raise ValueError("JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN are required")
    jql = config.get("jql") or ""
    if not jql:
        raise ValueError("jira config missing jql")
    query = urllib.parse.urlencode({"jql": jql, "fields": "summary,status,labels", "maxResults": "100"})
    url = f"{base}/rest/api/2/search?{query}"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"jira http {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"jira unreachable: {exc.reason}") from exc
    issues = payload.get("issues") if isinstance(payload, dict) else None
    if not isinstance(issues, list):
        raise ValueError("jira response missing issues")
    return [row for row in issues if isinstance(row, dict)]


def _upsert(rows: list[dict], item: dict) -> str:
    for i, existing in enumerate(rows):
        if existing.get("id") == item["id"]:
            merged = dict(existing)
            merged.update(item)
            rows[i] = merged
            return "update"
    rows.append(item)
    return "insert"


def apply_mapped(inventory: dict, mapped: list[dict], config: dict) -> tuple[dict, list[dict]]:
    doc_prefix = config.get("id_prefix") or DOC_PREFIX_DEFAULT
    ctl_prefix = config.get("control_prefix") or CTL_PREFIX_DEFAULT
    updated = copy.deepcopy(inventory)
    docs = updated.setdefault("docs", [])
    controls = updated.setdefault("controls", [])
    writes: list[dict] = []
    for item in mapped:
        if not item:
            continue
        doc = item["doc"]
        if not str(doc["id"]).startswith(str(doc_prefix).rstrip("-")):
            continue
        op = _upsert(docs, doc)
        writes.append({"op": f"{op}_doc", "id": doc["id"], "key": item.get("key")})
        control = item.get("control")
        if control and str(control["id"]).startswith(str(ctl_prefix).rstrip("-")):
            op_c = _upsert(controls, control)
            writes.append({"op": f"{op_c}_control", "id": control["id"], "key": item.get("key")})
    return updated, writes


def sync_issues(inventory: dict, issues: list[dict], config: dict) -> tuple[int, dict, list[dict], list[dict]]:
    browse = config.get("browse_base") or os.environ.get("JIRA_BASE_URL") or ""
    mapped = []
    skipped = []
    for raw in issues:
        norm = normalize_issue(raw, browse)
        row = map_issue(norm, config)
        if row is None:
            skipped.append({"key": norm.get("key"), "reason": "no brand and no journey"})
            continue
        mapped.append(row)
    updated, writes = apply_mapped(inventory, mapped, config)
    fails = lint_inventory(updated)
    if fails:
        return 1, inventory, writes, fails
    return 0, updated, writes, skipped
