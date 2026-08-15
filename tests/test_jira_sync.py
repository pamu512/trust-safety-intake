import json
import shutil
from pathlib import Path

from trust_intake.cli import main
from trust_intake.inventory_lint import lint_inventory, load_inventory
from trust_intake.jira_sync import load_issues_json, load_jira_config, map_issue, normalize_issue, sync_issues

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "inventory" / "product-inventory.yaml"
CONFIG = ROOT / "inventory" / "jira.yaml"
FIXTURE = ROOT / "tests" / "fixtures" / "jira" / "issues.json"


def test_yaml_generic_brand_keys_map():
    config = load_jira_config(CONFIG)
    assert "brand 1" in (config.get("brand_labels") or {})
    norm = normalize_issue(
        {"key": "TS-2", "title": "Cap", "status": "To Do", "labels": ["brand-2", "promo"]},
        "",
    )
    row = map_issue(norm, config)
    assert row is not None
    assert row["doc"]["brands"] == ["foodpanda"]


def test_brand_names_on_ticket_do_not_map():
    config = load_jira_config(CONFIG)
    norm = normalize_issue(
        {"key": "TS-8", "title": "Named brand", "status": "To Do", "labels": ["foodpanda", "account"]},
        "",
    )
    assert map_issue(norm, config) is None


def test_custom_board_labels():
    config = load_jira_config(CONFIG)
    config["brand_labels"] = {"foodpanda": ["brand-fp", "panda"]}
    config["journey_labels"] = {"account": ["tns-ato"]}
    config["control_labels"] = ["tns-capability"]
    norm = normalize_issue(
        {
            "key": "TS-7",
            "title": "ATO step-up",
            "status": "In Progress",
            "labels": ["brand-fp", "tns-ato", "tns-capability"],
        },
        "",
    )
    row = map_issue(norm, config)
    assert row is not None
    assert row["doc"]["brands"] == ["foodpanda"]
    assert row["doc"]["journey"] == "account"
    assert row["control"]["id"] == "ctl-jira-ts-7"


def test_skips_no_brand_no_journey():
    config = load_jira_config(CONFIG)
    norm = normalize_issue({"key": "TS-1", "title": "Q3 hardening", "labels": ["platform"]}, "")
    assert map_issue(norm, config) is None


def test_maps_flat_and_jira_api_shapes():
    config = load_jira_config(CONFIG)
    issues = load_issues_json(FIXTURE)
    inv = load_inventory(SEED)
    code, updated, writes, skipped = sync_issues(inv, issues, config)
    assert code == 0
    assert lint_inventory(updated) == []
    assert any(s.get("key") == "TS-1" for s in skipped)
    docs = {d["id"]: d for d in updated["docs"]}
    assert docs["doc-jira-ts-1234"]["title"] == "Account takeover step-up Q3"
    assert docs["doc-jira-ts-1234"]["status"] == "open"
    assert docs["doc-jira-ts-1234"]["journey"] == "account"
    assert docs["doc-jira-ts-1234"]["brands"] == ["foodpanda"]
    assert docs["doc-jira-ts-1234"]["type"] == "ticket"
    assert "€12M" not in json.dumps(docs["doc-jira-ts-1234"])
    assert docs["doc-jira-ts-99"]["title"] == "Promo stacking cap"
    assert docs["doc-jira-ts-99"]["journey"] == "promo"
    controls = {c["id"]: c for c in updated["controls"]}
    assert controls["ctl-jira-ts-1234"]["status"] == "pilot"
    assert controls["ctl-jira-ts-1234"]["related_docs"] == ["doc-jira-ts-1234"]
    assert "ctl-jira-ts-99" not in controls
    assert controls["ctl-refund-static"]["name"] == "Repeat claimant rule"
    assert {w["id"] for w in writes} >= {"doc-jira-ts-1234", "ctl-jira-ts-1234", "doc-jira-ts-99"}


def test_cli_json_dry_run_does_not_write(tmp_path: Path):
    inv = tmp_path / "product-inventory.yaml"
    shutil.copy(SEED, inv)
    before = inv.read_text(encoding="utf-8")
    code = main(
        [
            "inventory-sync",
            "--from",
            "json",
            "--file",
            str(FIXTURE),
            "--dry-run",
            "--inventory",
            str(inv),
            "--jira-config",
            str(CONFIG),
        ]
    )
    assert code == 0
    assert inv.read_text(encoding="utf-8") == before


def test_cli_json_writes_only_jira_prefix(tmp_path: Path):
    inv = tmp_path / "product-inventory.yaml"
    shutil.copy(SEED, inv)
    code = main(
        [
            "inventory-sync",
            "--from",
            "json",
            "--file",
            str(FIXTURE),
            "--inventory",
            str(inv),
            "--jira-config",
            str(CONFIG),
        ]
    )
    assert code == 0
    data = load_inventory(inv)
    assert any(d["id"] == "doc-jira-ts-1234" for d in data["docs"])
    assert any(d["id"] == "doc-ex-1" for d in data["docs"])
    assert inv.with_suffix(".md").is_file()


def test_cli_jira_without_env_exits_2(tmp_path: Path, monkeypatch):
    inv = tmp_path / "product-inventory.yaml"
    shutil.copy(SEED, inv)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    code = main(
        [
            "inventory-sync",
            "--from",
            "jira",
            "--inventory",
            str(inv),
            "--jira-config",
            str(CONFIG),
        ]
    )
    assert code == 2
