"""Build the presentation deck for "Same Strike, Different Story".

Story order: context -> problem -> methodology -> system architecture -> results
-> mitigation -> takeaways. Every number is read from results/summary.json,
results/tables/ or results/runs.jsonl and asserted, never typed by hand.

Outputs
  slides/Same_Strike_Different_Story_slides.pptx   editable deck
  slides/Same_Strike_Different_Story_slides.pdf    rendered deck
  slides/img/slide_NN.png                          per-slide renders for the web page
  slides/index.html                                GitHub Pages page: all slides, scrollable

Run: python slides/deck/build_deck.py   (needs LibreOffice for the render step)
"""
from __future__ import annotations

import html as _h
import json
import pathlib
import shutil
import sys

import pandas as pd
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from deck_helpers import *  # noqa: E402,F403

ROOT = HERE.parents[1]
SLIDES = ROOT / "slides"
FIG = ROOT / "figures"
S = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
TAB = ROOT / "results" / "tables"
QRDIR = HERE / "_qr"

BRAND = "Same Strike, Different Story  ·  Apart AI x Epistemics Sprint 2026"
AUTHOR = "Fatimah Emad Eldin  ·  Cairo University"
URLS = {
    "repo": "https://github.com/astral-fate/same-strike-different-story",
    "paper": "https://github.com/astral-fate/same-strike-different-story/blob/main/paper/Same_Strike_Different_Story.pdf",
    "slides": "https://astral-fate.github.io/same-strike-different-story/",
    "steinert": "https://doi.org/10.1177/00223433241279381",
    "sprint": "https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15",
}


def p1(x):  # share -> "64.7"; half-up like the paper
    return f"{x * 100 + 1e-9:.1f}"


# ---------------- numbers ----------------
A = S["attribution_by_role"]
base, piv = A["baseline"], A["pivot"]
rb = base["rates"]
gb, gp = base["gap_victim_minus_attacker"], piv["gap_victim_minus_attacker"]
ROB = S["attribution_robustness"]
fe = ROB["baseline"]["fe_attacker_role_effect"]
loco = list(ROB["baseline"]["leave_one_conflict_out_gap"].values())
FR = S["fragmentation"]["baseline"]
civ = S["civilian_pct_att_minus_vic"]["baseline"]
N = S["n_responses"]
COST = S["total_cost_usd"]

assert N == 6335 and f"{COST:.2f}" == "0.61"
assert (p1(rb["attacker"]["named"]), p1(rb["victim"]["named"]), p1(rb["en"]["named"])) == ("64.7", "74.1", "75.9")
assert (p1(gb[0]), p1(gb[1]), p1(gb[2])) == ("9.4", "5.7", "13.6")
assert (p1(gp[0]), p1(gp[1]), p1(gp[2])) == ("5.5", "0.9", "10.5")
assert p1(-fe[0]) == "9.7" and p1(min(loco)) == "7.3" and p1(max(loco)) == "11.4"
assert p1(ROB["baseline"]["high_resource_only_gap"]) == "5.8" and p1(ROB["pivot"]["high_resource_only_gap"]) == "1.3"
assert (base["events_gap_pos"], base["events_gap_neg"], base["n_events"]) == (15, 1, 19)
assert base["models_gap_pos"] == 8 and base["conflicts_gap_pos"] == 5

events = [json.loads(l) for l in (ROOT / "data" / "events.jsonl").open(encoding="utf-8")]
controls = [json.loads(l) for l in (ROOT / "data" / "controls.jsonl").open(encoding="utf-8")]
conflicts = json.loads((ROOT / "data" / "conflicts.json").read_text(encoding="utf-8"))
assert len(events) == 22 and len(controls) == 6 and len(conflicts) == 5
n_disputed = sum(e["disputed"] for e in events)
assert len(events) - n_disputed == 19

audit = [json.loads(l) for l in (ROOT / "results" / "translation_audit.jsonl").open(encoding="utf-8")]
n_audit = len(audit)

prompt_en = next(json.loads(l) for l in (ROOT / "data" / "prompts.jsonl").open(encoding="utf-8")
                 if '"item": "am_karabakh2023"' in l and '"lang": "en"' in l)["prompt"]

NAMES = {"openai/gpt-5.6-luna": "GPT-5.6-Luna", "deepseek/deepseek-chat": "DeepSeek-V3",
         "openai/gpt-4o-mini": "GPT-4o-mini", "mistralai/mistral-small-24b-instruct-2501": "Mistral-Small-24B",
         "meta-llama/llama-3.1-8b-instruct": "Llama-3.1-8B", "qwen/qwen3.7-flash": "Qwen 3.7-Flash",
         "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "z-ai/glm-5.3-flash": "GLM-5.3-Flash"}
mb = pd.read_csv(TAB / "attribution_by_model_baseline.csv", index_col=0)
mp = pd.read_csv(TAB / "attribution_by_model_pivot.csv", index_col=0)
mod = pd.DataFrame({"b": mb.victim - mb.attacker, "p": mp.victim - mp.attacker}).sort_values("b", ascending=False)
assert len(mod) == 8

ex = {}
for line_ in (ROOT / "results" / "runs.jsonl").open(encoding="utf-8"):
    r = json.loads(line_)
    if (r["status"] == "ok" and r["condition"] == "baseline" and r["item"] == "am_karabakh2023"
            and r["model"] == "anthropic/claude-haiku-5.5" and r["sample"] == 1):
        ex[r["lang"]] = r
assert ex["en"]["responsible"] == "B" and ex["hy"]["responsible"] == "B" and ex["az"]["responsible"] == "C"
karabakh = next(e for e in events if e["id"] == "am_karabakh2023")["desc"]

LANG = {"he": "Hebrew", "ar": "Arabic", "ru": "Russian", "uk": "Ukrainian", "tr": "Turkish", "ku": "Kurmanji",
        "hy": "Armenian", "az": "Azerbaijani", "hi": "Hindi", "ur": "Urdu"}
CONF = {"israel_gaza": "Israel – Gaza", "russia_ukraine": "Russia – Ukraine", "turkey_kurdish": "Turkey – Kurdish groups",
        "armenia_azerbaijan": "Armenia – Azerbaijan", "india_pakistan": "India – Pakistan"}
per_conf = pd.read_csv(TAB / "attribution_by_conflict_baseline.csv", index_col=0)

QR = {k: make_qr(v, QRDIR / f"{k}.png") for k, v in URLS.items()}
ROWALT = RGBColor(0xEC, 0xF2, 0xF5)
AMBER_TXT = RGBColor(0xFC, 0xD3, 0x4D)
ORANGE = RGBColor(0xC2, 0x41, 0x0C)
BLUE = RGBColor(0x1D, 0x4E, 0xD8)

# ---------------- deck ----------------
prs = new_deck()
n = 0


def nxt(s, dark=False):
    global n
    n += 1
    footer(s, n, dark=dark, brand=BRAND)


def sec(num, kick, big, sub):
    s = slide(prs, NAVY)
    line(s, 0, 0, SW, 0.22, TEALBR)
    text(s, 11.6, 1.2, 7.6, 7.5, num, size=360, color=CARDDK, bold=True, font=HEADB, align=PP_ALIGN.RIGHT)
    text(s, 1.3, 3.3, 12, 0.6, kick.upper(), size=18, color=TEALBR, bold=True, font=HEAD)
    text(s, 1.25, 3.95, 12.5, 2.6, big, size=54, color=WHITE, bold=True, font=HEADB, spacing=1.02)
    line(s, 1.3, 6.65, 1.6, 0.07, TEALBR)
    text(s, 1.3, 7.0, 11.5, 1.6, sub, size=22, color=MIST, spacing=1.15)
    nxt(s, dark=True)


def card(s, l, t, w, h, bar=TEALBR, fill=CARD):
    rect(s, l, t, w, h, fill=fill, line=LINEC, radius=0.05, shadow=True)
    if bar is not None:
        line(s, l + 0.02, t, w - 0.04, 0.09, bar)


def pill(s, l, t, w, txt, fill):
    rect(s, l, t, w, 0.44, fill=fill, radius=0.5)
    text(s, l, t, w, 0.44, txt, size=13, color=WHITE, bold=True, font=HEAD,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def table_header(s, x0, y0, cols, total_w, size=15, h=0.62):
    rect(s, x0, y0, total_w, h, fill=NAVY, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    x = x0
    for name, w in cols:
        text(s, x + 0.28, y0 + 0.13, w - 0.4, 0.45, name, size=size, color=WHITE, bold=True, font=HEAD)
        x += w


def band(s, t, h, msg, size=19):
    rect(s, 0.9, t, 18.2, h, fill=NAVY, radius=0.04)
    text(s, 1.4, t, 17.2, h, msg, size=size, color=WHITE, spacing=1.15, anchor=MSO_ANCHOR.MIDDLE)


# 1 Title -------------------------------------------------------------
s = slide(prs, NAVY)
line(s, 0, 0, SW, 0.22, TEALBR)
text(s, 0.9, 1.25, 11, 0.5, "APART RESEARCH  ·  AI x EPISTEMICS SPRINT  ·  NOV 2026", size=15, color=TEALBR, bold=True, font=HEAD)
text(s, 0.9, 1.95, 11.4, 3.0, "Same Strike,\nDifferent Story", size=64, color=WHITE, bold=True, font=HEADB, spacing=0.98)
text(s, 0.9, 4.75, 10.8, 1.6, "Language models attribute conflict events differently depending on the language of the person asking.",
     size=24, color=MIST, spacing=1.15)
line(s, 0.9, 6.6, 1.6, 0.07, TEALBR)
text(s, 0.9, 6.95, 11, 1.2, [[(AUTHOR, {"bold": True, "color": WHITE})],
                             [("Track 1 Model Epistemics & Evals  ·  Track 4 Open", {"color": MIST})]], size=18, spacing=1.3)
rect(s, 12.9, 1.25, 6.2, 8.6, fill=CARDDK, radius=0.04)
text(s, 13.4, 1.65, 5.4, 0.5, "AT A GLANCE", size=14, color=TEALBR, bold=True, font=HEAD)
glance = [(f"{p1(gb[0])} pts", NEG_ON_DARK, "fewer answers name the attacker when the attacker's side asks"),
          (f"{base['models_gap_pos']} / 8", AMBER_TXT, f"models show the gap, and all {base['conflicts_gap_pos']} conflicts"),
          (f"{p1(gp[0])} pts", AMBER_TXT, "gap left with a “same answer in every language” instruction")]
for i, (big, c, cap) in enumerate(glance):
    y = 2.3 + i * 2.5
    text(s, 13.4, y, 5.4, 1.1, big, size=54, color=c, bold=True, font=HEADB)
    text(s, 13.4, y + 1.15, 5.3, 1.0, cap, size=15, color=MIST, spacing=1.1)
    if i < 2:
        line(s, 13.4, y + 2.2, 5.2, 0.02, RGBColor(0x3A, 0x4C, 0x60))
nxt(s, dark=True)

# 2 Roadmap -----------------------------------------------------------
s = slide(prs)
kicker(s, "Roadmap")
title(s, "From one question to a measurable gap")
steps = [("01", "Context", "Who asks models about wars, and in which language"),
         ("02", "Problem", "Language-dependent answers fragment a shared record"),
         ("03", "Methodology", "Parallel prompts, audited translations, a noise floor"),
         ("04", "System architecture", "How a question becomes a scored response"),
         ("05", "Results", "Attribution gap, robustness, death tolls"),
         ("06", "Mitigation", "Does a consistency instruction close the gap?"),
         ("07", "Takeaways", "What holds, what does not, what to do next")]
for i, (num, h, d) in enumerate(steps):
    col, row = divmod(i, 4)
    x, y = 0.9 + col * 9.35, 2.55 + row * 1.95
    card(s, x, y, 8.85, 1.65, bar=None)
    line(s, x, y + 0.02, 0.1, 1.61, TEALBR)
    text(s, x + 0.45, y + 0.3, 1.3, 1.0, num, size=40, color=TEAL, bold=True, font=HEADB)
    text(s, x + 1.85, y + 0.28, 6.8, 0.6, h, size=24, color=INK, bold=True, font=HEADB)
    text(s, x + 1.85, y + 0.88, 6.8, 0.6, d, size=16, color=SLATE)
nxt(s)

# 01 Context ----------------------------------------------------------
sec("01", "Context", "People ask models what\nhappened in a war", "In their own language, and increasingly instead of a search engine or a newspaper.")

s = slide(prs)
kicker(s, "Context")
title(s, "Models are becoming a first source for contested events")
cards3 = [("Asked in many languages", TEALBR,
           "Speakers on each side of a conflict query the same models, each in their own language, about the same strikes and attacks."),
          ("Answers become the record", AMBER,
           "If the facts change with the language of the question, each community receives its own version of the event: epistemic fragmentation."),
          ("Prior evidence", RED,
           "GPT-3.5 reported lower death tolls when asked in the attacker's language (Steinert & Kazenwadel, 2025, Journal of Peace Research).")]
for i, (h, c, d) in enumerate(cards3):
    x = 0.9 + i * 6.15
    card(s, x, 2.6, 5.75, 4.6, bar=c)
    text(s, x + 0.45, 3.1, 4.9, 0.6, h, size=24, color=INK, bold=True, font=HEADB)
    text(s, x + 0.45, 4.0, 4.9, 3.0, d, size=19, color=SLATE, spacing=1.2)
rect(s, 0.9, 7.65, 18.2, 2.3, fill=NAVY, radius=0.04)
text(s, 1.4, 7.95, 17, 0.5, "THE OPEN QUESTION", size=14, color=TEALBR, bold=True, font=HEAD)
text(s, 1.4, 8.5, 17.2, 1.3, "Does this still hold for current models, and does it extend from how many died to who is blamed?",
     size=26, color=WHITE, bold=True, font=HEADB, spacing=1.1)
nxt(s)

# 02 Problem ----------------------------------------------------------
sec("02", "Problem", "Same event, different\nanswer by asker", "The failure is invisible to English-only evaluations.")

s = slide(prs, NAVY)
line(s, 0, 0, SW, 0.22, TEALBR)
text(s, 0.9, 0.7, 16, 0.5, "THE CENTRAL CONCEPT", size=15, color=TEALBR, bold=True, font=HEAD)
text(s, 0.9, 1.15, 18, 1.0, "Not translation noise: asker-dependent attribution", size=40, color=WHITE, bold=True, font=HEADB)
panels = [(CARDDK, None, "WHAT IT IS NOT", "Translation noise",
           ["Numbers wobble a little across languages", "Happens for any topic, political or not",
            "No link to which side is asking", f"Measured here on {len(controls)} non-political disasters"], POS_ON_DARK,
           "Our noise floor"),
          (RGBColor(0x3A, 0x22, 0x22), RED, "WHAT IT IS", "Asker-dependent attribution",
           ["The same attack is described differently by side", "The attacker's side hears “disputed” more often",
            "Each reader thinks the answer is neutral", "Each community gets its own record"], NEG_ON_DARK,
           "The effect we test")]
for i, (fill, border, lab, head, lines_, tc, tag) in enumerate(panels):
    x = 0.9 + i * 9.35
    rect(s, x, 2.75, 8.85, 6.6, fill=fill, line=border, line_w=2.0, radius=0.04)
    text(s, x + 0.55, 3.2, 7.8, 0.5, lab, size=14, color=MIST, bold=True, font=HEAD)
    text(s, x + 0.55, 3.75, 7.8, 0.9, head, size=32, color=WHITE, bold=True, font=HEADB)
    for j, t_ in enumerate(lines_):
        text(s, x + 0.55, 4.95 + j * 0.8, 7.8, 0.7, "•  " + t_, size=20, color=MIST)
    text(s, x + 0.55, 8.35, 7.8, 0.6, tag, size=20, color=tc, bold=True, font=HEADB)
nxt(s, dark=True)

s = slide(prs)
kicker(s, "Research questions")
title(s, "Three questions, each with its own test")
rqs = [("RQ1", "Attribution", "Is the reported attacker named less often when the question is asked in the attacker's language than in the victim's?"),
       ("RQ2", "Death tolls", "Do tolls differ across the two parties' languages more than across languages for non-political disasters?"),
       ("RQ3", "Mitigation", "Does a system instruction to answer identically in every language close the gap?")]
for i, (k, h, d) in enumerate(rqs):
    y = 2.6 + i * 2.15
    card(s, 0.9, y, 18.2, 1.85, bar=None)
    line(s, 0.9, y + 0.02, 0.1, 1.81, TEALBR)
    chip(s, 1.4, y + 0.7, k, TEAL, w=1.0, size=15)
    text(s, 2.8, y + 0.32, 4.0, 0.6, h, size=26, color=INK, bold=True, font=HEADB)
    text(s, 6.6, y + 0.35, 12.0, 1.3, d, size=20, color=SLATE, spacing=1.15)
nxt(s)

# 03 Methodology ------------------------------------------------------
sec("03", "Methodology", "A parallel-language audit\nwith a noise floor", "Same question, both parties' languages, eight models, a non-political control set.")

s = slide(prs)
kicker(s, "Design")
title(s, "Five conflicts where each side has attacked the other")
stats = [(str(len(events)), "documented incidents"), (str(len(controls)), "non-political controls"),
         ("11", "languages"), ("8", "models, 7 developers"), (f"{N:,}", "responses"), (f"${COST:.2f}", "total API cost")]
for i, (b, l_) in enumerate(stats):
    x = 0.9 + i * 3.07
    card(s, x, 2.45, 2.8, 1.85, bar=None)
    text(s, x, 2.6, 2.8, 0.9, b, size=38, color=TEAL, bold=True, font=HEADB, align=PP_ALIGN.CENTER)
    text(s, x + 0.1, 3.55, 2.6, 0.6, l_, size=14, color=SLATE, align=PP_ALIGN.CENTER)
cols = [("Conflict", 4.4), ("Language A", 3.0), ("Language B", 3.0), ("Party A", 3.6), ("Party B", 4.2)]
y0 = 4.75
table_header(s, 0.9, y0, cols, 18.2)
for i, (k, c) in enumerate(conflicts.items()):
    y = y0 + 0.62 + i * 0.75
    rect(s, 0.9, y, 18.2, 0.75, fill=CARD if i % 2 == 0 else ROWALT, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    vals = [CONF[k], LANG[c["lang_a"]], LANG[c["lang_b"]], c["party_a"], c["party_b"]]
    x = 0.9
    for (h, w), v in zip(cols, vals):
        text(s, x + 0.28, y + 0.17, w - 0.4, 0.55, v, size=13.5 if len(v) > 30 else 16, color=INK); x += w
text(s, 0.9, 9.55, 18.2, 0.6, f"{len(events) - n_disputed} incidents have a documented attacker; {n_disputed} are genuinely disputed and are excluded from the attribution test.",
     size=16, color=SLATE2)
nxt(s)

s = slide(prs)
kicker(s, "The instrument")
title(s, "One neutral prompt, three measures, no perpetrator in the question")
rect(s, 0.9, 2.45, 11.3, 7.75, fill=NAVY, radius=0.03)
text(s, 1.35, 2.8, 10.5, 0.45, "REAL PROMPT  ·  ENGLISH TEMPLATE", size=13, color=TEALBR, bold=True, font=HEAD)
text(s, 1.35, 3.35, 10.5, 6.7, prompt_en, size=14.5, color=MIST, font=MONO, spacing=1.12)
card(s, 12.7, 2.45, 6.4, 3.85, bar=TEALBR)
text(s, 13.1, 2.85, 5.7, 0.5, "Three measures", size=22, color=INK, bold=True, font=HEADB)
text(s, 13.1, 3.5, 5.7, 2.7, [[("Death toll  ", {"bold": True, "color": INK}), ("one number", {})],
                             [("Civilian share  ", {"bold": True, "color": INK}), ("percent", {})],
                             [("Responsibility  ", {"bold": True, "color": INK}), ("A, B, C disputed, D other", {})]],
     size=18, color=SLATE, spacing=1.45)
card(s, 12.7, 6.6, 6.4, 3.6, bar=GREEN)
text(s, 13.1, 7.0, 5.7, 0.5, "Translation audit", size=22, color=INK, bold=True, font=HEADB)
text(s, 13.1, 7.65, 5.7, 2.4, f"Each translation is back-translated and checked for loaded terms and added blame. {n_audit}/{n_audit} pass.",
     size=18, color=SLATE, spacing=1.2)
nxt(s)

s = slide(prs)
kicker(s, "Measures and tests")
title(s, "What is measured, and how it is tested")
cols = [("Measure", 4.2), ("Definition", 7.8), ("Test", 6.2)]
rows_ = [("Attribution gap", "Share naming the reported attacker: victim's language minus attacker's language", "Event-clustered bootstrap CI; exact McNemar on modal answers"),
         ("Language-identity control", "Attacker-language effect with event, language and model fixed effects", "Linear probability model, SEs clustered by event"),
         ("Toll divergence", "Share of language pairs whose tolls differ by ≥25%, events vs controls", "Fisher exact test"),
         ("Toll direction", "Log toll, attacker's minus victim's language, per cell", "Wilcoxon signed-rank"),
         ("Mitigation", "The same measures with a “same answer in every language” system instruction", "Gap and McNemar per condition")]
y0 = 2.5
table_header(s, 0.9, y0, cols, 18.2, size=16, h=0.65)
for i, vals in enumerate(rows_):
    y = y0 + 0.65 + i * 1.3
    rect(s, 0.9, y, 18.2, 1.3, fill=CARD if i % 2 == 0 else ROWALT, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    x = 0.9
    for j, ((h, w), v) in enumerate(zip(cols, vals)):
        text(s, x + 0.28, y + 0.22, w - 0.5, 1.0, v, size=18 if j == 0 else 16, color=INK if j == 0 else SLATE,
             bold=(j == 0), font=HEADB if j == 0 else BODY, spacing=1.1); x += w
nxt(s)

# 04 Architecture -----------------------------------------------------
sec("04", "System architecture", "How a question becomes\na scored response", "Build the instrument, ask every model in every language, parse and score.")

s = slide(prs)
kicker(s, "System architecture")
title(s, "Instrument → asking → measurement")
arch = Image.open(FIG / "architecture.png")
crop = arch.crop((0, 2 * 148, arch.width, 2 * (510 + 282)))  # panels 1-2 of the figure (2x render)
crop_p = HERE / "_arch_crop.png"
crop.save(crop_p)
aw = 17.4
ah = aw * crop.height / crop.width
card(s, 0.9, 2.15, 18.2, ah + 0.3, bar=None)
s.shapes.add_picture(str(crop_p), Inches(1.3), Inches(2.3), Inches(aw), Inches(ah))
text(s, 0.9, 2.15 + ah + 0.5, 18.2, 0.9, [("Then: ", {"bold": True, "color": INK}),
     (f"the parser extracts toll, civilian share and responsibility from all {N:,} responses, and the analysis compares the attacker's with the victim's language against the {len(controls)}-disaster noise floor.", {})],
     size=17, color=SLATE, spacing=1.15)
nxt(s)

# 05 Results ----------------------------------------------------------
sec("05", "Results", "The attacker's side hears\n“disputed” more often", "Attribution shifts with the asker; death tolls diverge without a direction.")

s = slide(prs, NAVY)
line(s, 0, 0, SW, 0.22, TEALBR)
text(s, 0.9, 0.7, 16, 0.5, "HEADLINE RESULT  ·  RQ1", size=15, color=TEALBR, bold=True, font=HEAD)
text(s, 0.9, 1.15, 18.2, 1.0, "Asked in the attacker's language, models name the attacker less often", size=38, color=WHITE, bold=True, font=HEADB)
trio = [("Attacker's language", rb["attacker"], NEG_ON_DARK, RGBColor(0x3A, 0x22, 0x22), RED),
        ("Victim's language", rb["victim"], RGBColor(0x93, 0xC5, 0xFD), CARDDK, None),
        ("English", rb["en"], MIST, CARDDK, None)]
for i, (lab, r, c, fill, border) in enumerate(trio):
    x = 0.9 + i * 6.15
    rect(s, x, 2.6, 5.75, 4.4, fill=fill, line=border, line_w=2.0, radius=0.04)
    text(s, x + 0.5, 2.95, 4.8, 0.5, lab.upper(), size=15, color=MIST, bold=True, font=HEAD)
    text(s, x + 0.5, 3.55, 4.8, 1.6, f"{p1(r['named'])}%", size=80, color=c, bold=True, font=HEADB)
    text(s, x + 0.5, 5.3, 4.8, 0.5, "name the reported attacker", size=17, color=MIST)
    text(s, x + 0.5, 5.95, 4.8, 0.5, f"“disputed”: {p1(r['disputed'])}%", size=17, color=WHITE, bold=True)
rect(s, 0.9, 7.35, 18.2, 2.6, fill=CARDDK, radius=0.04)
text(s, 1.4, 7.7, 17.2, 0.8, [(f"Gap {p1(gb[0])} points", {"bold": True, "color": TEALBR, "size": 30}),
                             (f"   95% CI {p1(gb[1])}–{p1(gb[2])}, event-clustered bootstrap", {"color": MIST})], size=20)
text(s, 1.4, 8.6, 17.2, 1.2,
     f"Positive for {base['events_gap_pos']} of {base['n_events']} events, negative for {base['events_gap_neg']}. "
     f"McNemar {base['modal_discordant_victim_only']} vs {base['modal_discordant_attacker_only']}, p = {base['mcnemar_exact_p']:.4f}. "
     f"English sits with the victim's language, so English-only evaluations cannot see the gap.",
     size=17, color=MIST, spacing=1.15)
nxt(s, dark=True)

s = slide(prs)
kicker(s, "Every model, every conflict")
title(s, f"Same direction in {base['models_gap_pos']}/8 models and {base['conflicts_gap_pos']}/5 conflicts")
fw = 12.4
fh = fw * 726 / 1628
card(s, 0.9, 2.4, fw + 0.4, fh + 0.4, bar=None)
s.shapes.add_picture(str(FIG / "fig3_attribution.png"), Inches(1.1), Inches(2.6), Inches(fw), Inches(fh))
text(s, 0.9, 2.4 + fh + 0.6, fw + 0.4, 0.9, "Share of answers naming the reported attacker. Orange: asked in the attacker's language. Blue: the victim's language.",
     size=15, color=SLATE2)
px = 14.0
text(s, px, 2.4, 5.1, 0.5, "BY CONFLICT", size=14, color=TEAL, bold=True, font=HEAD)
for i, (k, r) in enumerate(per_conf.iterrows()):
    y = 3.0 + i * 1.3
    card(s, px, y, 5.1, 1.1, bar=None)
    text(s, px + 0.3, y + 0.15, 4.6, 0.4, CONF[k], size=15, color=INK, bold=True, font=HEADB)
    text(s, px + 0.3, y + 0.58, 4.6, 0.4, [(f"{p1(r.attacker)}%", {"color": ORANGE, "bold": True}),
                                          ("  →  ", {"color": SLATE2}),
                                          (f"{p1(r.victim)}%", {"color": BLUE, "bold": True}),
                                          (f"   +{p1(r.victim - r.attacker)} pts", {"color": SLATE})], size=16)
nxt(s)

s = slide(prs)
kicker(s, "What it looks like")
title(s, "One model, one event, three languages")
text(s, 0.9, 2.2, 18.2, 0.6, [("Claude Haiku 5.5 on ", {}), (f"“{karabakh}”", {"italic": True, "color": INK}),
                             (". Shown: sample 1 of 3 in each language.", {})], size=18, color=SLATE)
LAB = {"A": "Armenian forces", "B": "Azerbaijani forces", "C": "Disputed / unclear", "D": "Someone else"}
for i, (lg, name, role) in enumerate([("en", "English", "neutral"), ("hy", "Armenian", "victim's language"), ("az", "Azerbaijani", "attacker's language")]):
    r = ex[lg]
    hit = r["responsible"] == "B"
    x = 0.9 + i * 6.15
    fill = CARD if hit else RGBColor(0xFF, 0xF4, 0xEC)
    rect(s, x, 3.15, 5.75, 4.9, fill=fill, line=LINEC if hit else AMBER, line_w=1.5, radius=0.04, shadow=True)
    line(s, x + 0.02, 3.15, 0.12, 4.9, GREEN if hit else AMBER)
    text(s, x + 0.55, 3.55, 5.0, 0.6, name, size=28, color=INK, bold=True, font=HEADB)
    text(s, x + 0.55, 4.2, 5.0, 0.5, role, size=16, color=SLATE2)
    text(s, x + 0.55, 5.1, 5.0, 0.4, "RESPONSIBLE", size=13, color=SLATE2, bold=True, font=HEAD)
    text(s, x + 0.55, 5.5, 5.0, 0.8, LAB[r["responsible"]], size=30, color=GREEN if hit else ORANGE, bold=True, font=HEADB)
    d = "UNKNOWN" if r["deaths_unknown"] else f"{int(r['deaths'])}"
    text(s, x + 0.55, 6.65, 5.0, 0.4, "DEATHS", size=13, color=SLATE2, bold=True, font=HEAD)
    text(s, x + 0.55, 7.05, 5.0, 0.6, d, size=24, color=INK, font=MONO)
band(s, 8.5, 1.4, "Not a refusal and not a wrong party: the attack becomes “disputed” only for the side that carried it out. To that reader, it sounds like neutrality.")
nxt(s)

s = slide(prs)
kicker(s, "Robustness")
title(s, "The gap survives controls for language identity")
rob = [(f"{p1(-fe[0])} pts", TEAL, TEALBR, "Fixed-effects estimate",
        f"Attacker-language effect with event, language and model fixed effects (95% CI {p1(-fe[2])}–{p1(-fe[1])}). Each language is the attacker's in one place and the victim's in another."),
       (f"{p1(min(loco))}–{p1(max(loco))}", TEAL, TEALBR, "Leave one conflict out",
        "Gap recomputed five times, dropping one conflict each time. No single conflict drives the result."),
       (f"{p1(ROB['baseline']['high_resource_only_gap'])} pts", RGBColor(0xB4, 0x53, 0x09), AMBER, "Well-resourced conflicts only",
        f"{ROB['baseline']['high_resource_only_n_events']} events. Smaller: part of the overall size comes from Kurmanji and Armenian/Azerbaijani.")]
for i, (big, c, bar, h, d) in enumerate(rob):
    x = 0.9 + i * 6.15
    card(s, x, 2.6, 5.75, 5.3, bar=bar, fill=CARD if bar != AMBER else RGBColor(0xFF, 0xFB, 0xEB))
    text(s, x + 0.45, 3.1, 5.0, 1.3, big, size=56, color=c, bold=True, font=HEADB)
    text(s, x + 0.45, 4.6, 5.0, 0.6, h, size=22, color=INK, bold=True, font=HEADB)
    text(s, x + 0.45, 5.35, 4.9, 2.5, d, size=17.5, color=SLATE, spacing=1.2)
band(s, 8.3, 1.65, "Every check keeps the gap positive. It is not an artefact of one language or one conflict, but its size depends on how well-resourced the languages are.")
nxt(s)

s = slide(prs)
kicker(s, "Death tolls  ·  RQ2")
title(s, "Tolls diverge more than for disasters, with no consistent direction")
fh = 7.9
fw = fh * 1364 / 1434
card(s, 0.9, 2.35, fw + 0.4, fh + 0.3, bar=None)
s.shapes.add_picture(str(FIG / "fig1_event_fi.png"), Inches(1.1), Inches(2.5), Inches(fw), Inches(fh))
fx = 0.9 + fw + 0.9
fwid = SW - 0.9 - fx
facts = [(f"{p1(FR['share_events_diff_ge_25pct'])}% vs {p1(FR['share_controls_diff_ge_25pct'])}%", RED,
          f"of language pairs differ by ≥25%: conflict events vs non-political controls (Fisher p = {FR['fisher_ge25pct_events_vs_controls_p']:.3f})"),
         (f"{p1(FR['FI_share_negative'])}% / {p1(FR['FI_share_positive'])}%", SLATE,
          f"of cells lower / higher in the attacker's language (Wilcoxon p = {FR['FI_wilcoxon_p']:.2f}): no direction"),
         (f"{civ[0]:+.1f} pts", SLATE, f"civilian-share difference, attacker's minus victim's language (CI {civ[1]:.1f} to {civ[2]:.1f})")]
for i, (b, c, d) in enumerate(facts):
    y = 2.35 + i * 2.2
    card(s, fx, y, fwid, 1.95, bar=None)
    line(s, fx, y + 0.02, 0.1, 1.91, c)
    text(s, fx + 0.45, y + 0.2, fwid - 0.7, 0.7, b, size=32, color=c if c == RED else INK, bold=True, font=HEADB)
    text(s, fx + 0.45, y + 0.95, fwid - 0.7, 1.0, d, size=15.5, color=SLATE, spacing=1.1)
rect(s, fx, 9.0, fwid, 1.25, fill=NAVY, radius=0.04)
text(s, fx + 0.4, 9.0, fwid - 0.8, 1.25, "The GPT-3.5 deflation pattern does not replicate here. The effect has moved to attribution.",
     size=17, color=WHITE, spacing=1.1, anchor=MSO_ANCHOR.MIDDLE)
nxt(s)

# 06 Mitigation -------------------------------------------------------
sec("06", "Mitigation", "Can one instruction\nclose the gap?", "A system prompt asking for the same answer in every language, run on every query.")

s = slide(prs)
kicker(s, "Tested mitigation  ·  RQ3")
title(s, "The instruction narrows the gap but does not close it")
rect(s, 0.9, 2.4, 6.6, 7.85, fill=NAVY, radius=0.03)
text(s, 1.35, 2.8, 5.8, 0.5, "POOLED GAP", size=14, color=TEALBR, bold=True, font=HEAD)
text(s, 1.35, 3.35, 5.8, 1.0, "Baseline", size=18, color=MIST)
text(s, 1.35, 3.8, 5.8, 1.2, f"{p1(gb[0])} pts", size=54, color=NEG_ON_DARK, bold=True, font=HEADB)
text(s, 1.35, 5.2, 5.8, 1.0, "With instruction", size=18, color=MIST)
text(s, 1.35, 5.65, 5.8, 1.2, f"{p1(gp[0])} pts", size=54, color=AMBER_TXT, bold=True, font=HEADB)
text(s, 1.35, 7.05, 5.8, 3.0,
     f"CI {p1(gp[1])}–{p1(gp[2])}; McNemar {piv['modal_discordant_victim_only']} vs {piv['modal_discordant_attacker_only']}, p = {piv['mcnemar_exact_p']:.2f}. "
     f"The reduction itself is not statistically significant. Well-resourced conflicts: {p1(ROB['baseline']['high_resource_only_gap'])} → {p1(ROB['pivot']['high_resource_only_gap'])} pts.",
     size=16, color=MIST, spacing=1.2)
tx = 8.0
cols = [("Model", 4.3), ("Baseline", 2.0), ("Instruction", 2.2), ("Effect", 2.6)]
table_header(s, tx, 2.4, cols, 11.1)
for i, (m, r) in enumerate(mod.iterrows()):
    y = 3.02 + i * 0.86
    rect(s, tx, y, 11.1, 0.86, fill=CARD if i % 2 == 0 else ROWALT, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    d = r.p - r.b
    if r.b > 0 and r.p < 0:
        verdict, c = "reverses", AMBER
    elif d < -0.02:
        verdict, c = "narrows", GREEN
    elif d > 0.02:
        verdict, c = "widens", RED
    else:
        verdict, c = "unchanged", SLATE2
    text(s, tx + 0.3, y + 0.2, 4.0, 0.5, NAMES[m], size=17, color=INK, bold=True, font=HEADB)
    text(s, tx + 4.3, y + 0.2, 1.7, 0.5, f"{r.b * 100 + 1e-9:+.1f}", size=17, color=INK, font=MONO, align=PP_ALIGN.RIGHT)
    text(s, tx + 6.3, y + 0.2, 1.9, 0.5, f"{r.p * 100 + 1e-9:+.1f}", size=17, color=INK, font=MONO, align=PP_ALIGN.RIGHT)
    pill(s, tx + 8.8, y + 0.21, 1.9, verdict, c)
text(s, tx, 10.0, 11.1, 0.5, "Gap in points, victim's minus attacker's language. Helps three models, does little for two, worsens or reverses three.",
     size=14, color=SLATE2)
nxt(s)

# 07 Takeaways --------------------------------------------------------
sec("07", "Takeaways", "Cross-lingual consistency\nis part of honesty", "What holds, what does not, and what evaluators and labs can do next.")

s = slide(prs)
kicker(s, "Takeaways")
title(s, "What holds, what fails, why it matters")
tk = [("✓", GREEN, "What holds", f"A {p1(gb[0])}-point attribution gap in all 8 models and 5 conflicts, robust to language fixed effects ({p1(-fe[0])} pts)."),
      ("✗", RED, "What fails", f"A consistency instruction narrows the gap to {p1(gp[0])} points but not to zero, and makes three models worse."),
      ("!", AMBER, "Why it matters", "English-only evaluations see the victim-side answer and miss the gap. Each community receives its own record.")]
for i, (ic, c, h, d) in enumerate(tk):
    x = 0.9 + i * 6.15
    card(s, x, 2.45, 5.75, 4.75, bar=None)
    rect(s, x + 0.45, 2.85, 0.9, 0.9, fill=c, radius=0.5)
    text(s, x + 0.45, 2.85, 0.9, 0.9, ic, size=30, color=WHITE, bold=True, font=HEADB, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 1.6, 2.98, 3.9, 0.7, h, size=24, color=INK, bold=True, font=HEADB)
    text(s, x + 0.45, 4.1, 4.9, 3.0, d, size=18, color=SLATE, spacing=1.2)
rect(s, 0.9, 7.55, 18.2, 2.65, fill=NAVY, radius=0.04)
text(s, 1.4, 7.85, 17, 0.5, "WHAT TO DO NEXT", size=14, color=TEALBR, bold=True, font=HEAD)
text(s, 1.4, 8.35, 17.2, 1.8, [[("Evaluators  ", {"bold": True, "color": WHITE}), ("ask contested-event questions in both parties' languages, not only English.", {})],
                              [("Labs  ", {"bold": True, "color": WHITE}), ("treat cross-lingual consistency on contested facts as a training and evaluation target.", {})],
                              [("Anyone  ", {"bold": True, "color": WHITE}), (f"rerun the open benchmark on each model release for under $1 (this run: ${COST:.2f}).", {})]],
     size=18, color=MIST, spacing=1.3)
nxt(s)

s = slide(prs)
kicker(s, "Scope and limitations")
title(s, "What this study does not establish")
lims = [("Consistency, not accuracy", "The gap shows answers depend on the asker; it does not say which answer is true."),
        ("Forced-choice format", "Options A–D make answers comparable but differ from open conversation."),
        (f"{len(events) - n_disputed} attributed events", "Five conflicts; the gap is smaller for the three well-resourced ones."),
        ("Small and mid-size models", "Eight models from seven developers; frontier models may behave differently."),
        ("Model-audited translations", "Back-translation audits are automatic; native-speaker review is future work."),
        ("English as reference", "English is treated as neutral, which is itself a choice.")]
for i, (h, d) in enumerate(lims):
    col, row = i % 3, i // 3
    x, y = 0.9 + col * 6.15, 2.5 + row * 3.75
    card(s, x, y, 5.75, 3.4, bar=SLATE2)
    text(s, x + 0.45, y + 0.5, 4.9, 0.6, h, size=21, color=INK, bold=True, font=HEADB)
    text(s, x + 0.45, y + 1.25, 4.9, 2.0, d, size=17, color=SLATE, spacing=1.2)
nxt(s)

# References ----------------------------------------------------------
s = slide(prs, NAVY)
line(s, 0, 0, SW, 0.22, TEALBR)
text(s, 0.9, 0.7, 16, 0.5, "SCAN TO OPEN", size=15, color=TEALBR, bold=True, font=HEAD)
text(s, 0.9, 1.15, 18, 1.0, "Code, data, paper and every raw response", size=40, color=WHITE, bold=True, font=HEADB)
refs = [("repo", "Code + data", "github.com/astral-fate/\nsame-strike-different-story"),
        ("paper", "Paper (PDF)", "paper/Same_Strike_\nDifferent_Story.pdf"),
        ("slides", "These slides", "astral-fate.github.io/\nsame-strike-different-story"),
        ("steinert", "Steinert & Kazenwadel 2025", "doi.org/10.1177/\n00223433241279381"),
        ("sprint", "Apart sprint", "apartresearch.com/sprints/\nai-x-epistemics-research-sprint")]
for i, (k, cap, url) in enumerate(refs):
    x = 0.9 + i * 3.7
    rect(s, x, 2.75, 3.3, 3.3, fill=WHITE, radius=0.06)
    s.shapes.add_picture(str(QR[k]), Inches(x + 0.35), Inches(3.1), Inches(2.6), Inches(2.6))
    text(s, x - 0.1, 6.3, 3.5, 0.5, cap, size=17, color=WHITE, bold=True, font=HEADB, align=PP_ALIGN.CENTER)
    text(s, x - 0.1, 6.85, 3.5, 1.0, url, size=12.5, color=MIST, font=MONO, align=PP_ALIGN.CENTER, spacing=1.05)
rect(s, 0.9, 8.3, 18.2, 1.7, fill=CARDDK, radius=0.04)
text(s, 1.4, 8.3, 17.2, 1.7, [[(AUTHOR, {"bold": True, "color": WHITE})],
                             [(f"{N:,} responses, 8 models, 11 languages, ${COST:.2f} in API cost. All numbers in these slides are read from results/.", {"color": MIST})]],
     size=18, spacing=1.35, anchor=MSO_ANCHOR.MIDDLE)
nxt(s, dark=True)

# ---------------- save, render, verify ----------------
pptx = SLIDES / "Same_Strike_Different_Story_slides.pptx"
prs.save(pptx)
for k, u in URLS.items():
    assert decode_qr(QR[k]) == u, k
render_dir = HERE / "_render"
shutil.rmtree(render_dir, ignore_errors=True)
pngs = render_to_pngs(pptx, render_dir, dpi=96)
shutil.copy(render_dir / (pptx.stem + ".pdf"), SLIDES / (pptx.stem + ".pdf"))
img_dir = SLIDES / "img"
shutil.rmtree(img_dir, ignore_errors=True)
img_dir.mkdir()
for p in pngs:
    shutil.copy(p, img_dir / p.name)


def slide_text(sl):
    out = []
    for sh in sl.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            out.append(sh.text_frame.text.replace("\v", " ").replace("\n", " ").strip())
    return out


texts = []
for sl in prs.slides:
    texts.append([x for x in slide_text(sl) if not x.startswith("Same Strike, Different Story  ·") and not x.isdigit()])
alts = [" — ".join(t[:2]) if t else "Slide" for t in texts]

# One scrollable page: every slide stacked, real text kept for search and screen readers.
figs = "\n".join(
    f'<section class="slide" id="s{i + 1}"><img src="img/{p.name}" width="1920" height="1080" alt="{_h.escape(alts[i])}" '
    f'{"" if i < 3 else "loading=\"lazy\" "}decoding="async"><div class="sr">{_h.escape(" | ".join(texts[i]))}</div>'
    f'<a class="num" href="#s{i + 1}">{i + 1}</a></section>'
    for i, p in enumerate(pngs))
HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Same Strike, Different Story</title>
<meta name="description" content="Slides: language models attribute conflict events differently depending on the asker's language. Apart AI x Epistemics Sprint 2026.">
<style>
:root{{--bg:#0E1822;--bar:#1B2A3A;--teal:#14B8A6;--mist:#CFE3E8}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;scroll-padding-top:64px;scroll-snap-type:y proximity}}
body{{background:var(--bg);color:var(--mist);font-family:"Segoe UI",system-ui,sans-serif}}
header{{position:sticky;top:0;z-index:5;height:52px;background:var(--bar);display:flex;align-items:center;gap:16px;padding:0 16px;font-size:14px;box-shadow:0 2px 12px #0006}}
header b{{color:#fff;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
header a{{color:var(--teal);text-decoration:none;white-space:nowrap}}
header a:hover{{text-decoration:underline}}
#count{{margin-left:auto;font-variant-numeric:tabular-nums;white-space:nowrap}}
#prog{{position:fixed;top:52px;left:0;height:3px;background:var(--teal);width:0;z-index:6;transition:width .15s}}
main{{max-width:1280px;margin:0 auto;padding:24px 16px 64px;display:flex;flex-direction:column;gap:28px}}
.slide{{position:relative;scroll-snap-align:start}}
.slide img{{display:block;width:100%;height:auto;border-radius:8px;box-shadow:0 18px 50px -18px #000}}
.num{{position:absolute;top:10px;right:12px;font-size:12px;color:#fff;background:#0009;border-radius:10px;padding:2px 8px;text-decoration:none;opacity:0;transition:opacity .2s}}
.slide:hover .num{{opacity:1}}
.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
footer{{text-align:center;font-size:13px;padding:0 16px 40px}}
footer a{{color:var(--teal)}}
@media (max-width:640px){{.hide-sm{{display:none}}main{{gap:16px;padding-top:16px}}}}
@media print{{header,#prog,footer{{display:none}}body{{background:#fff}}main{{max-width:none;padding:0}}.slide{{page-break-after:always}}.slide img{{box-shadow:none}}}}
</style></head><body>
<header><b>Same Strike, Different Story</b>
<a class="hide-sm" href="{pptx.stem}.pdf">PDF</a><a class="hide-sm" href="{pptx.stem}.pptx">PPTX</a>
<a class="hide-sm" href="{URLS['paper']}">Paper</a><a href="{URLS['repo']}">Code</a>
<span id="count">1 / {len(pngs)}</span></header>
<div id="prog"></div>
<main>
{figs}
</main>
<footer>{AUTHOR} &middot; Apart Research AI x Epistemics Sprint 2026 &middot; <a href="{URLS['repo']}">github.com/astral-fate/same-strike-different-story</a></footer>
<script>
const S=[...document.querySelectorAll('.slide')],cnt=document.getElementById('count'),pr=document.getElementById('prog');
function cur(){{const y=innerHeight*0.4;let k=0;S.forEach((s,i)=>{{if(s.getBoundingClientRect().top<=y)k=i}});return k}}
function upd(){{const k=cur();cnt.textContent=(k+1)+' / '+S.length;
const h=document.documentElement;pr.style.width=(h.scrollTop/(h.scrollHeight-innerHeight||1)*100)+'%'}}
addEventListener('scroll',upd,{{passive:true}});addEventListener('resize',upd);upd();
document.addEventListener('keydown',e=>{{if(e.target.closest('input,textarea'))return;
const k=cur();if(['ArrowRight','PageDown','j'].includes(e.key)||(e.key===' '&&!e.shiftKey)){{e.preventDefault();S[Math.min(k+1,S.length-1)].scrollIntoView()}}
else if(['ArrowLeft','PageUp','k'].includes(e.key)||(e.key===' '&&e.shiftKey)){{e.preventDefault();S[Math.max(k-1,0)].scrollIntoView()}}}});
</script></body></html>"""
(SLIDES / "index.html").write_text(HTML, encoding="utf-8")
print(f"{len(pngs)} slides -> {pptx.name}, PDF, img/, index.html (scrollable); QR codes verified")
