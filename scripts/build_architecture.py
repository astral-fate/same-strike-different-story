"""Architecture figure: how the instrument is built, how the models are asked, and what the analysis found.

    python scripts/build_architecture.py   -> figures/architecture.svg (+ .png via headless Chrome)

Every number is read from data/ and results/ and the headline ones are asserted, so a re-scored run fails loudly
instead of drawing stale numbers.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _svgkit import Svg, ACCENT, ACCENT_BG, BASE, UP, TEAL, LINE, NAVY  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "architecture.svg"


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


EV = jl(ROOT / "data" / "events.jsonl")
CT = jl(ROOT / "data" / "controls.jsonl")
CF = json.load(open(ROOT / "data" / "conflicts.json", encoding="utf-8"))
PR = jl(ROOT / "data" / "prompts.jsonl")
AU = jl(ROOT / "results" / "translation_audit.jsonl")
S = json.load(open(ROOT / "results" / "summary.json", encoding="utf-8"))

n_ev, n_ct, n_conf = len(EV), len(CT), len(CF)
n_attr = sum(e["attacker"] is not None for e in EV)
n_disp = sum(bool(e["disputed"]) for e in EV)
langs = {l for c in CF.values() for l in (c["lang_a"], c["lang_b"])} | {"en"}
audit_ok = sum(a.get("status") == "ok" and a.get("equivalent") and not a.get("loaded") and a.get("labels_ok") for a in AU)
A = S["attribution_by_role"]
rb, b, p = A["baseline"]["rates"], A["baseline"], A["pivot"]
fe = S["attribution_robustness"]["baseline"]["fe_attacker_role_effect"]
FR = S["fragmentation"]["baseline"]
import csv  # noqa: E402
_m = {k: {r["model"]: float(r["victim"]) - float(r["attacker"]) for r in csv.DictReader(open(
    ROOT / "results" / "tables" / f"attribution_by_model_{k}.csv", encoding="utf-8"))} for k in ("baseline", "pivot")}
_d = [_m["pivot"][m] - _m["baseline"][m] for m in _m["baseline"]]
n_narrow = sum(d < -0.02 for d in _d)
n_same = sum(abs(d) <= 0.02 for d in _d)
n_worse = sum(d > 0.02 for d in _d) + sum(_m["pivot"][m] < 0 < _m["baseline"][m] and _m["pivot"][m] - _m["baseline"][m] < -0.02 for m in _m["baseline"])
n_narrow -= sum(_m["pivot"][m] < 0 < _m["baseline"][m] and _m["pivot"][m] - _m["baseline"][m] < -0.02 for m in _m["baseline"])
assert (n_narrow, n_same, n_worse) == (3, 2, 3), (n_narrow, n_same, n_worse)

EPS = 1e-9
pct = lambda v: f"{100 * v + EPS:.1f}%"          # half-up, same rounding as the paper
pts = lambda v: f"{100 * v + EPS:.1f}"

assert (n_ev, n_ct, n_conf, n_attr, n_disp, len(langs), len(PR)) == (22, 6, 5, 19, 3, 11, 132)
assert (len(AU), audit_ok) == (104, 104), (len(AU), audit_ok)
assert S["n_responses"] == 6335
assert (pct(rb["attacker"]["named"]), pct(rb["victim"]["named"]), pct(rb["en"]["named"])) == ("64.7%", "74.1%", "75.9%")
assert (pts(b["gap_victim_minus_attacker"][0]), pts(p["gap_victim_minus_attacker"][0]), pts(-fe[0])) == ("9.4", "5.5", "9.7")

ATT, VIC = "#C2410C", "#1D4ED8"                  # the paper's figure colours for attacker's / victim's language
W, H = 1600, 1250
s = Svg(W, H)
t = s.text


def node(x, y, w, h, lines, fill="#F1F5F9", stroke=LINE, sw=1.2, dash=False):
    """Box with a bold first line and smaller lines under it, the block centred vertically."""
    s.box(x, y, w, h, fill, stroke, rx=10, sw=sw, dash=dash)
    hs = [21] + [18] * (len(lines) - 1)
    top = y + (h - sum(hs)) / 2 + 15
    for i, ln in enumerate(lines):
        t(x + w / 2, top + sum(hs[:i]), ln, "h3" if i == 0 else "s", "middle")


def panel(y, h, label):
    s.box(40, y, W - 80, h, "#FFFFFF", LINE, rx=14, sw=1.2)
    t(60, y - 16, label, "h2")


# ---- title -------------------------------------------------------------------------------------------------------
t(60, 62, "Same Strike, Different Story: how the measurement works", "h1")
t(60, 96, f"Each conflict incident is asked in the languages of both parties and in English; {n_ct} non-political "
          "disasters go through the same pipeline as a noise floor.", "t")
x = 60
for lab, col in (("asked in the attacker's language", ATT), ("asked in the victim's language", VIC),
                 ("English", BASE), ("tested mitigation", ACCENT), ("negative control", TEAL)):
    x += s.chip(x, 114, lab, col) + 10

# ---- 1 · instrument ----------------------------------------------------------------------------------------------
Y1 = 190
panel(Y1, 250, "1 · The instrument: one neutral question in eleven languages")
node(70, Y1 + 30, 300, 100, [f"{n_ev} conflict incidents", f"{n_conf} conflicts · place, date and type only",
                             f"{n_attr} attributed · {n_disp} contested"])
node(70, Y1 + 145, 300, 80, [f"{n_ct} control disasters", "no partisan side · asked in all 11 languages"],
     fill="#ECFEFF", stroke=TEAL, sw=1.6)
node(430, Y1 + 60, 300, 130, ["One English template", "deaths · civilian share · responsible",
                              "A) party A   B) party B", "C) disputed or unclear   D) someone else"])
node(790, Y1 + 60, 230, 130, ["Translate", "Claude Haiku 5.5", f"{len(langs) - 1} languages", "answer labels kept in Latin"])
node(1080, Y1 + 60, 250, 130, ["Back-translate + audit", "GPT-4o-mini", f"{audit_ok}/{len(AU)} pass",
                               "equivalent · no loaded terms"])
node(1390, Y1 + 60, 160, 130, [f"{len(PR)} prompts", "frozen in", "data/prompts.jsonl"])
s.path(f"M370,{Y1 + 80} C400,{Y1 + 80} 400,{Y1 + 110} 430,{Y1 + 110}")
s.path(f"M370,{Y1 + 185} C400,{Y1 + 185} 400,{Y1 + 150} 430,{Y1 + 150}", col=TEAL)
for x1, x2 in ((730, 790), (1020, 1080), (1330, 1390)):
    s.arrow(x1, Y1 + 125, x2, Y1 + 125)

# ---- 2 · asking --------------------------------------------------------------------------------------------------
Y2 = 510
panel(Y2, 270, "2 · Asking: 8 models × 2 conditions × 3 samples")
node(70, Y2 + 70, 250, 110, ["Prompt in one language", "the attacker's, the victim's,", "or English"])
node(390, Y2 + 30, 300, 80, ["Baseline", "the translated prompt only"], fill="#F8FAFC", stroke=BASE, sw=1.6)
node(390, Y2 + 140, 300, 90, ["Language-invariance instruction", "fixed English system message:",
                              "same answer for every language"], fill=ACCENT_BG, stroke=ACCENT, sw=2)
s.chip(470, Y2 + 128, "tested mitigation", ACCENT)
s.path(f"M320,{Y2 + 110} C355,{Y2 + 110} 355,{Y2 + 70} 390,{Y2 + 70}")
s.path(f"M320,{Y2 + 140} C355,{Y2 + 140} 355,{Y2 + 185} 390,{Y2 + 185}", col=ACCENT)
node(760, Y2 + 55, 340, 150, ["8 models via OpenRouter", "GPT-4o-mini · GPT-5.6-Luna · Claude Haiku 5.5",
                              "DeepSeek-V3 · Qwen 3.7-Flash · GLM-5.3-Flash", "Mistral-Small-24B · Llama-3.1-8B",
                              "temperature 0.7 · 3 samples per cell"])
s.path(f"M690,{Y2 + 70} C725,{Y2 + 70} 725,{Y2 + 110} 760,{Y2 + 110}")
s.path(f"M690,{Y2 + 185} C725,{Y2 + 185} 725,{Y2 + 150} 760,{Y2 + 150}", col=ACCENT)
node(1160, Y2 + 55, 190, 150, [f"{S['n_responses']:,} responses", "each appended", "as it returns;", "reruns resume"])
node(1400, Y2 + 55, 150, 150, ["Parser", "native digits", "separators, ranges", "A / B / C / D"])
s.arrow(1100, Y2 + 130, 1160, Y2 + 130)
s.arrow(1350, Y2 + 130, 1400, Y2 + 130)

# ---- 3 · analysis ------------------------------------------------------------------------------------------------
Y3 = 850
panel(Y3, 330, "3 · Analysis and what it found")
CW, CH, CY = 470, 280, Y3 + 25
xs = [60, 565, 1070]

# card 1: attribution
s.card(xs[0], CY, CW, CH, "Attribution · primary", NAVY)
rows = [("Attacker's language", rb["attacker"]["named"], ATT), ("Victim's language", rb["victim"]["named"], VIC),
        ("English", rb["en"]["named"], BASE)]
t(xs[0] + 24, CY + 72, "Share of answers naming the reported attacker", "s")
for i, (lab, v, col) in enumerate(rows):
    yy = CY + 88 + i * 30
    t(xs[0] + 24, yy + 15, lab, "t2")
    s.bar(xs[0] + 180, yy + 2, 200, 18, "#E2E8F0")
    s.bar(xs[0] + 180, yy + 2, 200 * v, 18, col)
    t(xs[0] + 390, yy + 16, pct(v), "t2b")
g = b["gap_victim_minus_attacker"]
t(xs[0] + 24, CY + 210, f"Gap {pts(g[0])} points (95% CI {pts(g[1])}–{pts(g[2])})", "t2b")
t(xs[0] + 24, CY + 232, f"Fixed effects for event, language, model: {pts(-fe[0])} points", "s")
t(xs[0] + 24, CY + 252, f"Same direction in {b['models_gap_pos']}/8 models and {b['conflicts_gap_pos']}/5 conflicts", "s")

# card 2: death tolls
s.card(xs[1], CY, CW, CH, "Death tolls · against the controls", TEAL)
t(xs[1] + 24, CY + 72, "Language pairs whose tolls differ by 25% or more", "s")
for i, (lab, v, col) in enumerate((("Conflict events", FR["share_events_diff_ge_25pct"], NAVY),
                                   ("Control disasters", FR["share_controls_diff_ge_25pct"], TEAL))):
    yy = CY + 88 + i * 30
    t(xs[1] + 24, yy + 15, lab, "t2")
    s.bar(xs[1] + 180, yy + 2, 200, 18, "#E2E8F0")
    s.bar(xs[1] + 180, yy + 2, 200 * v / 0.4, 18, col)
    t(xs[1] + 390, yy + 16, pct(v), "t2b")
t(xs[1] + 24, CY + 172, f"Fisher p = {FR['fisher_ge25pct_events_vs_controls_p']:.3f}", "s")
t(xs[1] + 24, CY + 210, "No consistent direction", "t2b")
t(xs[1] + 24, CY + 232, f"{pct(FR['FI_share_negative'])} of cells lower, {pct(FR['FI_share_positive'])} higher in the "
                        "attacker's language", "s")
t(xs[1] + 24, CY + 252, f"(Wilcoxon p = {FR['FI_wilcoxon_p']:.2f}): the GPT-3.5 pattern does not replicate", "s")

# card 3: mitigation
s.card(xs[2], CY, CW, CH, "Mitigation · language-invariance instruction", ACCENT)
t(xs[2] + 24, CY + 72, "Attribution gap, victim's minus attacker's language", "s")
for i, (lab, v, col) in enumerate((("Baseline", b["gap_victim_minus_attacker"][0], BASE),
                                   ("With instruction", p["gap_victim_minus_attacker"][0], ACCENT))):
    yy = CY + 88 + i * 30
    t(xs[2] + 24, yy + 15, lab, "t2")
    s.bar(xs[2] + 180, yy + 2, 200, 18, "#E2E8F0")
    s.bar(xs[2] + 180, yy + 2, 200 * v / 0.12, 18, col)
    t(xs[2] + 390, yy + 16, f"{pts(v)} pts", "t2b")
gp = p["gap_victim_minus_attacker"]
t(xs[2] + 24, CY + 172, f"With instruction: 95% CI {pts(gp[1])}–{pts(gp[2])}", "s")
t(xs[2] + 24, CY + 210, "Narrows the gap, does not close it", "t2b")
t(xs[2] + 24, CY + 232, f"Large drops for {n_narrow} models, none for {n_same},", "s")
t(xs[2] + 24, CY + 252, f"wider or reversed for {n_worse}", "s")

# ---- footer ------------------------------------------------------------------------------------------------------
y = Y3 + 330 + 34
t(60, y, f"Numbers from results/summary.json and data/ · {S['n_responses']:,} responses · US${S['total_cost_usd']:.2f} in API "
         "fees · CIs from a bootstrap over events · Apart Research AI x Epistemics Sprint, Nov 2026", "s")
assert y < H
OUT.parent.mkdir(exist_ok=True)
s.save(str(OUT))
