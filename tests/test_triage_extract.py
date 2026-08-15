from pathlib import Path

import pytest

from trust_intake.triage_extract import extract_card
from trust_intake.triage_read import read_document, read_sidecar

FIXTURE = Path("tests/fixtures/triage/repeat-claimant.md")


def test_md_extracts_brands_markets_euro(tmp_path, monkeypatch):
    text = FIXTURE.read_text()
    markets = {"SG": ["SG", "Singapore"], "HK": ["HK", "Hong Kong"]}
    card = extract_card(FIXTURE, text, {}, markets)
    assert card["brands"] == ["foodpanda"]
    assert card["markets"] == ["HK", "SG"]
    assert card["euro_impact"]["value"] == 2_500_000
    assert card["journey"] in {"claims-cancel", "unknown"}


def test_all_three_brands():
    markets = {}
    card = extract_card(Path("x.md"), "# X\nall three brands\n", {}, markets)
    assert card["brands"] == ["foodora", "foodpanda", "yemeksepeti"]


def test_sidecar_overrides_brands():
    card = extract_card(Path("x.md"), "# X\nfoodora\n", {"brands": ["foodpanda"]}, {})
    assert card["brands"] == ["foodpanda"]


def test_sidecar_brands_filtered_through_brands():
    card = extract_card(Path("x.md"), "# X\nfoodora\n", {"brands": ["acme", "foodpanda"]}, {})
    assert card["brands"] == ["foodpanda"]


def test_html_extracts_title_and_brand(tmp_path):
    path = tmp_path / "note.html"
    path.write_text("<h1>Title</h1><p>foodora Germany</p>", encoding="utf-8")
    text = read_document(path)
    markets = {"DE": ["DE", "Germany"]}
    card = extract_card(path, text, {}, markets)
    assert card["title"] == "Title"
    assert card["brands"] == ["foodora"]
    assert card["markets"] == ["DE"]


def test_docx_extracts_brand_and_euro(tmp_path):
    from docx import Document

    path = tmp_path / "note.docx"
    doc = Document()
    doc.add_heading("Docx Title", level=1)
    doc.add_paragraph("foodpanda Singapore. Exposure €1M.")
    doc.save(path)
    text = read_document(path)
    card = extract_card(path, text, {}, {"SG": ["SG", "Singapore"]})
    assert card["brands"] == ["foodpanda"]
    assert card["markets"] == ["SG"]
    assert card["euro_impact"]["value"] == 1_000_000


def test_sidecar_path_is_stem_meta_json(tmp_path):
    path = tmp_path / "repeat-claimant.md"
    path.write_text("# X\n", encoding="utf-8")
    (tmp_path / "repeat-claimant.meta.json").write_text('{"brands": ["foodora"]}', encoding="utf-8")
    (tmp_path / "repeat-claimant.md.meta.json").write_text('{"brands": ["yemeksepeti"]}', encoding="utf-8")
    assert read_sidecar(path) == {"brands": ["foodora"]}


def test_unsupported_suffix_raises(tmp_path):
    path = tmp_path / "note.xlsx"
    path.write_bytes(b"not-a-brd")
    with pytest.raises(ValueError, match="unsupported"):
        read_document(path)
