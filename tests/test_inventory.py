from pathlib import Path

from trust_intake.inventory_lint import CONTROL_STATUS, DOC_STATUS, lint_inventory, load_inventory
from trust_intake.inventory_render import render_inventory_md


def _ok() -> dict:
    return {
        "brands": ["foodora", "foodpanda", "yemeksepeti"],
        "journeys": [
            "account",
            "promo",
            "checkout",
            "claims-cancel",
            "payout",
            "cross-journey",
        ],
        "stack": [{"id": "rules", "name": "Rules engine", "layer": "decisioning", "notes": ""}],
        "controls": [
            {
                "id": "ctl-refund-static",
                "name": "Repeat claimant rule",
                "type": "rule",
                "journey": "claims-cancel",
                "brands": ["foodpanda"],
                "status": "live",
                "owner": "ops",
                "related_docs": ["doc-ex-1"],
            }
        ],
        "docs": [
            {
                "id": "doc-ex-1",
                "type": "brd",
                "title": "Repeat claimant static rule",
                "status": "shipped",
                "journey": "claims-cancel",
                "brands": ["foodpanda"],
                "link": "",
            }
        ],
    }


def test_lint_clean():
    assert lint_inventory(_ok()) == []


def test_lint_duplicate_id():
    data = _ok()
    data["stack"].append({"id": "rules", "name": "dup", "layer": "x", "notes": ""})
    assert any(f["code"] == "duplicate_id" for f in lint_inventory(data))


def test_lint_dangling_related_docs():
    data = _ok()
    data["controls"][0]["related_docs"] = ["missing"]
    assert any(f["code"] == "dangling_related_docs" for f in lint_inventory(data))


def test_render_contains_tables():
    md = render_inventory_md(_ok())
    assert "| ctl-refund-static |" in md
    assert "| doc-ex-1 |" in md


def test_live_token_stays_in_schema():
    assert "live" in CONTROL_STATUS
    assert "example" in CONTROL_STATUS
    assert "shipped" in DOC_STATUS
    assert "example" in DOC_STATUS


def test_load_seed_file():
    data = load_inventory(Path("inventory/product-inventory.yaml"))
    assert lint_inventory(data) == []
    ctl = next(c for c in data["controls"] if c["id"] == "ctl-refund-static")
    assert ctl["status"] == "example"
    assert ctl["status"] != "live"
    doc = next(d for d in data["docs"] if d["id"] == "doc-ex-1")
    assert doc["status"] == "example"
    assert doc["status"] != "shipped"
    md = render_inventory_md(data)
    assert "Example stub — not a live catalog." in md
    assert "foodpanda | example |" in md
