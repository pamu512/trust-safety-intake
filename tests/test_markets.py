from pathlib import Path

import yaml

from trust_intake.markets import lint_markets, load_markets, resolve_markets


def test_seed_lints_clean():
    raw = yaml.safe_load(Path("inventory/markets.yaml").read_text())
    assert lint_markets(raw) == []


def test_lint_duplicate_id():
    fails = lint_markets({"markets": [{"id": "SG", "aliases": []}, {"id": "SG", "aliases": []}]})
    assert any(f["code"] == "duplicate_id" for f in fails)


def test_singapore_alias():
    markets = {"SG": ["SG", "Singapore"], "DE": ["DE", "Germany"]}
    assert resolve_markets("Launch in Singapore and DE", markets) == ["DE", "SG"]


def test_iso_ids_case_sensitive_not_english_words():
    markets = load_markets(Path("inventory/markets.yaml"))
    assert resolve_markets("claims at 12%. no extra. my team. Singapore", markets) == ["SG"]
