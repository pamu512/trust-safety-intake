from pathlib import Path

from trust_intake.inventory_lint import load_inventory
from trust_intake.markets import load_markets
from trust_intake.triage import cluster_unify, label_cards, render_triage_md, run_triage

INV = load_inventory(Path("inventory/product-inventory.yaml"))
MARKETS = load_markets(Path("inventory/markets.yaml"))


def _metric(value, unit):
    if value is None:
        return {"value": None, "unit": unit, "source": "missing"}
    return {"value": value, "unit": unit, "source": "extract"}


def _card(title, brands, markets, journey="unknown", euro=None, volume=None, rate=None, id_="x"):
    return {
        "id": id_,
        "path": f"{id_}.md",
        "title": title,
        "brands": brands,
        "markets": markets,
        "journey": journey,
        "euro_impact": _metric(euro, "EUR"),
        "volume": _metric(volume, None),
        "rate": _metric(rate, "%"),
    }


def test_similar_titles_unify():
    cards = [
        _card("Repeat claimant static control", ["foodpanda"], ["SG"], "claims-cancel", euro=2_500_000, id_="a"),
        _card("Repeat claimant static rule", ["foodpanda"], ["HK"], "claims-cancel", euro=1_000_000, id_="b"),
    ]
    out = cluster_unify(cards)
    cluster_ids = {c["cluster_id"] for c in out}
    assert len(cluster_ids) == 1
    assert None not in cluster_ids
    assert all("unify" in c["labels"] for c in out)


def test_thin_single_brand_market_low_euro():
    cards = [_card("Small promo", ["foodora"], ["SG"], "promo", euro=50_000, id_="thin")]
    out = label_cards(cards, INV, 100_000)
    assert "deprioritise" in out[0]["labels"]
    assert "thin" in out[0]["reasons"]


def test_two_brands_no_numbers_high_priority_and_no_numbers():
    cards = [_card("Cross-brand promo", ["foodora", "foodpanda"], ["SG"], "promo", id_="wide")]
    out = label_cards(cards, INV, 100_000)
    assert "high-priority" in out[0]["labels"]
    assert "no-numbers" in out[0]["reasons"]
    assert "deprioritise" in out[0]["labels"]
    assert "thin" not in out[0]["reasons"]


def test_already_ships_seed_control():
    cards = [
        _card(
            "Repeat claimant static control",
            ["foodpanda"],
            ["SG"],
            "claims-cancel",
            euro=2_500_000,
            id_="rep",
        )
    ]
    out = label_cards(cards, INV, 100_000)
    assert "deprioritise" in out[0]["labels"]
    assert "already-ships" in out[0]["reasons"]
    assert out[0]["inventory_overlaps"]


def test_xlsx_warning_not_crash(tmp_path):
    (tmp_path / "x.xlsx").write_bytes(b"not-a-real-xlsx")
    (tmp_path / "ok.md").write_text("# A\nfoodora Singapore\n€2M\n")
    (tmp_path / "triage.json").write_text("{}")
    (tmp_path / "triage.md").write_text("old")
    (tmp_path / "ok.meta.json").write_text("{}")
    code, payload = run_triage(tmp_path, INV, MARKETS, 100000)
    assert code == 0
    assert payload["warnings"]
    assert payload["cards"]
    assert payload["min_euro"] == 100000
    assert "clusters" in payload
    assert all(c["id"] != "triage" for c in payload["cards"])
    md = render_triage_md(payload)
    for heading in ("High priority", "Unify", "Deprioritise", "Extraction gaps", "Warnings"):
        assert heading in md


def test_extraction_gap_not_deprioritised_solely():
    cards = [_card("No extract", [], [], "unknown", euro=500_000, id_="gap")]
    out = label_cards(cards, INV, 100_000)
    assert "extraction-gap" in out[0]["labels"]
    assert "deprioritise" not in out[0]["labels"]
    assert "thin" not in out[0]["reasons"]
