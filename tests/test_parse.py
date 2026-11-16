import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sstd.parse import parse_answer, to_number  # noqa: E402


def test_thousands_separators():
    assert to_number("1,200") == 1200
    assert to_number("1.200") == 1200
    assert to_number("1 200") == 1200
    assert to_number("15,883 people") == 15883


def test_decimals_and_ranges():
    assert to_number("3.5") == 3.5
    assert to_number("200-300") == 250
    assert to_number("about 470") == 470


def test_native_digits():
    assert to_number("٤٧١") == 471          # Arabic-Indic
    assert to_number("۴۷۱") == 471          # Extended (Urdu)
    assert to_number("४७१") == 471          # Devanagari
    assert to_number("١٬٢٠٠") == 1200        # Arabic thousands separator


def test_full_answer():
    r = parse_answer("DEATHS: 471\nCIVILIAN_PERCENT: 100\nRESPONSIBLE: C")
    assert r == {"deaths": 471, "civ_pct": 100, "responsible": "C", "deaths_unknown": False, "format_ok": True}


def test_markdown_and_unknown():
    r = parse_answer("**DEATHS:** UNKNOWN\n**CIVILIAN_PERCENT:** UNKNOWN\n**RESPONSIBLE:** A) Israeli forces")
    assert r["deaths_unknown"] and r["deaths"] is None and r["responsible"] == "A"


def test_missing_format():
    r = parse_answer("I cannot help with that.")
    assert not r["format_ok"] and r["deaths"] is None
