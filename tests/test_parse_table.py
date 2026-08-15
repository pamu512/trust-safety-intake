from pathlib import Path

from openpyxl import Workbook

from trust_intake.parse_table import parse_table


def test_csv_totals_and_yoy(tmp_path: Path):
    p = tmp_path / "loss.csv"
    p.write_text(
        "period,brand,loss_eur\n2024-01-01,foodpanda,100\n2025-01-01,foodpanda,128\n",
        encoding="utf-8",
    )
    facts = parse_table(p)
    table = facts["tables"][0]
    assert table["row_count"] == 2
    assert table["totals"]["loss_eur"] == 228
    yoy = next(d for d in facts["derived"] if d["method"] == "yoy")
    assert yoy["value"] == 0.28
    assert yoy["source"] == "csv"


def test_xlsx_multisheet_and_empty_warning(tmp_path: Path):
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "loss"
    ws1.append(["period", "loss_eur"])
    ws1.append(["2025-01-01", 50])
    ws2 = wb.create_sheet("empty")
    ws2.append(["period", "loss_eur"])
    path = tmp_path / "t.xlsx"
    wb.save(path)
    facts = parse_table(path)
    names = {t["name"] for t in facts["tables"]}
    assert names == {"loss", "empty"}
    empty = next(t for t in facts["tables"] if t["name"] == "empty")
    assert any("empty" in w.lower() or "single" in w.lower() or "no rows" in w.lower() for w in empty["warnings"])


def test_bad_euro_text_warns(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text("period,loss_eur\n2025-01-01,not-a-number\n", encoding="utf-8")
    facts = parse_table(p)
    assert facts["tables"][0]["warnings"]
