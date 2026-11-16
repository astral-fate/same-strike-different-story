"""Parse the labelled answer lines. Handles native digit systems and locale thousand separators."""
from __future__ import annotations

import re

# Arabic-Indic, Extended Arabic-Indic (Urdu/Persian), Devanagari.
_DIGITS = {}
for base in (0x0660, 0x06F0, 0x0966):
    for i in range(10):
        _DIGITS[chr(base + i)] = str(i)
_TRANS = str.maketrans({**_DIGITS, "٬": ",", "٫": ".", " ": " ", " ": " ", " ": " "})

_NUM = re.compile(r"\d+(?:[ .,']\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def to_number(s: str) -> float | None:
    """'1,200' / '1.200' / '1 200' -> 1200; '3.5' -> 3.5; ranges '200-300' -> midpoint."""
    s = s.translate(_TRANS)
    nums = []
    for m in _NUM.finditer(s):
        tok = m.group(0)
        if re.fullmatch(r"\d{1,3}(?:[ .,']\d{3})+", tok):  # pure thousands grouping
            nums.append(float(re.sub(r"[ .,']", "", tok)))
        elif re.fullmatch(r"\d{1,3}(?:[ .,']\d{3})+[.,]\d+", tok):
            nums.append(float(re.sub(r"[ .,']", "", tok[:-len(re.search(r"[.,]\d+$", tok).group(0))])))
        else:
            nums.append(float(tok.replace(",", ".")))
    if not nums:
        return None
    # range like "200-300" or "200 to 300": take the midpoint of the first two numbers
    if len(nums) >= 2 and re.search(r"\d\s*(?:-|–|—|to|~)\s*\d", s):
        return (nums[0] + nums[1]) / 2
    return nums[0]


def _line(text: str, label: str) -> str | None:
    m = re.search(rf"{label}\s*[:：]\s*(.+)", text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_answer(text: str) -> dict:
    text = text.replace("*", "")
    out = {"deaths": None, "civ_pct": None, "responsible": None,
           "deaths_unknown": False, "format_ok": False}
    d = _line(text, "DEATHS")
    if d is not None:
        out["format_ok"] = True
        if re.search(r"unknown|n/?a\b", d, re.IGNORECASE):
            out["deaths_unknown"] = True
        else:
            out["deaths"] = to_number(d)
            if out["deaths"] is None:
                out["deaths_unknown"] = True
    c = _line(text, "CIVILIAN_PERCENT")
    if c is not None and not re.search(r"unknown", c, re.IGNORECASE):
        v = to_number(c)
        out["civ_pct"] = v if v is not None and 0 <= v <= 100 else None
    r = _line(text, "RESPONSIBLE")
    if r is not None:
        m = re.search(r"\b([ABCD])\b", r.upper()) or re.match(r"([ABCD])", r.upper())
        out["responsible"] = m.group(1) if m else None
    return out
