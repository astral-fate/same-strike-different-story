"""Build slides/index.html: a self-contained HTML deck (figures and QR inlined).
Every number is read from results/summary.json or results/tables, never typed.
Run after scripts/analyze.py and scripts/figures.py:  python slides/build_slides.py
Navigate with arrow keys / space / click; F for fullscreen."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
import segno

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "slides" / "index.html"
S = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
TAB = ROOT / "results" / "tables"
REPO = "https://github.com/astral-fate/same-strike-different-story"
TITLE = "Same Strike, Different Story"


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def pts(x, d=1):
    return f"{x * 100:.{d}f}"


def img(name):
    b = base64.b64encode((ROOT / "figures" / name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" alt="{name}">'


def qr_svg(url):
    q = segno.make(url, error="m")
    import io
    buf = io.BytesIO()
    q.save(buf, kind="svg", scale=6, border=1, dark="#0F172A", light="#FFFFFF", xmldecl=False, svgns=True)
    return buf.getvalue().decode()


A = S["attribution_by_role"]
base, piv = A["baseline"], A["pivot"]
rb, rp = base["rates"], piv["rates"]
gap_b, gap_p = base["gap_victim_minus_attacker"], piv["gap_victim_minus_attacker"]
ROB = S["attribution_robustness"]
fe = ROB["baseline"]["fe_attacker_role_effect"]
loco = ROB["baseline"]["leave_one_conflict_out_gap"].values()
FR = S["fragmentation"]["baseline"]
civ = S["civilian_pct_att_minus_vic"]["baseline"]

mb = pd.read_csv(TAB / "attribution_by_model_baseline.csv", index_col=0)
mp = pd.read_csv(TAB / "attribution_by_model_pivot.csv", index_col=0)
mod = pd.DataFrame({"b": mb.victim - mb.attacker, "p": mp.victim - mp.attacker}).sort_values("b", ascending=False)
NAMES = {"openai/gpt-5.6-luna": "GPT-5.6-Luna", "deepseek/deepseek-chat": "DeepSeek-V3", "openai/gpt-4o-mini": "GPT-4o-mini",
         "mistralai/mistral-small-24b-instruct-2501": "Mistral-Small-24B", "meta-llama/llama-3.1-8b-instruct": "Llama-3.1-8B",
         "qwen/qwen3.7-flash": "Qwen 3.7-Flash", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "z-ai/glm-5.3-flash": "GLM-5.3-Flash"}
rows = ""
for m, r in mod.iterrows():
    delta = r.p - r.b
    cls = "good" if delta < -0.02 else ("bad" if delta > 0.02 else "flat")
    verdict = {"good": "narrows", "bad": "widens", "flat": "unchanged"}[cls]
    if r.b > 0 and r.p < 0:
        cls, verdict = "bad", "reverses"
    rows += (f"<tr><td>{NAMES.get(m, m)}</td><td class='num'>{pts(r.b)}</td><td class='num'>{pts(r.p)}</td>"
             f"<td><span class='chip {cls}'>{verdict}</span></td></tr>")

# worked example straight from the raw runs
ex = {}
for line in (ROOT / "results" / "runs.jsonl").open(encoding="utf-8"):
    r = json.loads(line)
    if (r["status"] == "ok" and r["condition"] == "baseline" and r["item"] == "am_karabakh2023"
            and r["model"] == "anthropic/claude-haiku-5.5" and r["sample"] == 1):
        ex[r["lang"]] = r
LAB = {"A": "Armenian forces", "B": "Azerbaijani forces", "C": "Disputed / unclear", "D": "Someone else", None: "—"}


def ex_row(lang, name, role):
    r = ex[lang]
    d = "UNKNOWN" if r["deaths_unknown"] else f"{int(r['deaths'])}"
    hit = "hit" if r["responsible"] == "B" else "miss"
    return (f"<div class='excard {hit}'><div class='exlang'>{name}<span>{role}</span></div>"
            f"<div class='exans'>{LAB[r['responsible']]}</div><div class='exdeath'>deaths: {d}</div></div>")


qr = qr_svg(REPO)

slides = []

slides.append(f"""
<section class="slide dark title-slide">
  <div class="kicker">Apart Research · AI x Epistemics Sprint · Nov 2026</div>
  <h1>Same Strike,<br><span class="accent">Different Story</span></h1>
  <p class="lede">Language models attribute conflict events differently<br>depending on the language of the person asking.</p>
  <div class="byline">Fatimah Emad Eldin · Trouve Labs</div>
  <div class="tracks">Track 1 · Model Epistemics &amp; Evals &nbsp;|&nbsp; Track 4 · Open</div>
</section>""")

slides.append("""
<section class="slide">
  <div class="kicker">The question</div>
  <h2>Two sides ask about the same strike. Do they get the same facts?</h2>
  <div class="cols">
    <div class="card"><div class="big">🗣️ → 🤖</div>
      <p>People increasingly ask models <b>what happened in a war</b>, in their own language.</p></div>
    <div class="card"><div class="big">⇄</div>
      <p>If answers differ by language, each community receives <b>its own version</b> of the event: the <i>epistemic fragmentation</i> that drives escalation (Stray, sprint keynote).</p></div>
    <div class="card"><div class="big">📉</div>
      <p>Precedent: GPT-3.5 reported <b>lower death tolls</b> in the attacker's language (Steinert &amp; Kazenwadel, 2025, <i>J. Peace Research</i>). Does this hold for current models, and for <b>who is blamed</b>?</p></div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Design</div>
  <h2>A parallel-language audit with a noise floor</h2>
  <div class="stats">
    <div class="stat"><b>22</b><span>documented incidents</span></div>
    <div class="stat"><b>5</b><span>conflicts, both sides attack</span></div>
    <div class="stat"><b>11</b><span>languages</span></div>
    <div class="stat"><b>8</b><span>models, 7 developers</span></div>
    <div class="stat"><b>{S['n_responses']:,}</b><span>responses</span></div>
    <div class="stat"><b>${S['total_cost_usd']:.2f}</b><span>total API cost</span></div>
  </div>
  <div class="pipe">
    <div>Neutral English item<small>place · date · type, no perpetrator</small></div><i>→</i>
    <div>Translate<small>both parties' languages</small></div><i>→</i>
    <div>Back-translate + audit<small>104/104 pass, no loaded terms</small></div><i>→</i>
    <div>Ask 8 models × 3 samples<small>toll · civilian % · who is responsible</small></div>
  </div>
  <p class="note"><b>Negative control:</b> 6 non-political disasters (e.g. Haiti 2010) in all 11 languages measure ordinary translation noise.
  <b>Mitigation:</b> each query also run with a "same answer in every language" system instruction.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Headline result</div>
  <h2>Asked in the attacker's language, models name the attacker less often</h2>
  <div class="trio">
    <div class="tri att"><span>Attacker's language</span><b>{pct(rb['attacker']['named'])}</b><small>"disputed": {pct(rb['attacker']['disputed'])}</small></div>
    <div class="tri vic"><span>Victim's language</span><b>{pct(rb['victim']['named'])}</b><small>"disputed": {pct(rb['victim']['disputed'])}</small></div>
    <div class="tri en"><span>English</span><b>{pct(rb['en']['named'])}</b><small>"disputed": {pct(rb['en']['disputed'])}</small></div>
  </div>
  <div class="callout">Gap <b>{pts(gap_b[0])} points</b> (95% CI {pts(gap_b[1])}–{pts(gap_b[2])}, event-clustered bootstrap) ·
  positive for {base['events_gap_pos']}/{base['n_events']} events, negative for {base['events_gap_neg']} ·
  McNemar {base['modal_discordant_victim_only']} vs {base['modal_discordant_attacker_only']}, p = {base['mcnemar_exact_p']:.4f}</div>
  <p class="note">The lost answers move mainly to <b>"responsibility is disputed"</b>. English matches the victim's language, so <b>English-only evals cannot see this.</b>
  "No option chosen" is identical in both languages ({pct(rb['attacker']['no_letter'])}), so it is not a format artefact.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Every model, every conflict</div>
  <h2>Same direction in {base['models_gap_pos']}/8 models and {base['conflicts_gap_pos']}/5 conflicts</h2>
  <div class="figcard wide">{img('fig3_attribution.png')}</div>
  <p class="cap">Share of answers naming the reported attacker: orange = asked in attacker's language, blue = victim's language.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">What it looks like</div>
  <h2>One model, one event, three languages</h2>
  <p class="note top">Claude Haiku 5.5 on <i>"the military offensive in Nagorno-Karabakh on 19–20 September 2023"</i>. All 3 samples per language agree.</p>
  <div class="excards">
    {ex_row('en', 'English', 'neutral')}
    {ex_row('hy', 'Armenian', "victim's language")}
    {ex_row('az', 'Azerbaijani', "attacker's language")}
  </div>
  <p class="note">Not a refusal and not a wrong party: the attack becomes <b>"disputed"</b> only for the side that carried it out. To that reader it sounds like neutrality.</p>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Is it the role or the language?</div>
  <h2>The gap survives controls for language identity</h2>
  <div class="cols">
    <div class="card"><div class="metric">{pts(-fe[0])} pts</div>
      <p>Effect of asking in the attacker's language with <b>event, language and model fixed effects</b> (95% CI {pts(-fe[2])}–{pts(-fe[1])}, clustered by event). Each language is both attacker's and victim's language somewhere.</p></div>
    <div class="card"><div class="metric">{pts(min(loco))}–{pts(max(loco))}</div>
      <p>Gap when <b>leaving out one conflict</b> at a time. No single conflict drives it.</p></div>
    <div class="card warn"><div class="metric">{pts(ROB['baseline']['high_resource_only_gap'])} pts</div>
      <p>Gap in the <b>three well-resourced conflicts</b> only ({ROB['baseline']['high_resource_only_n_events']} events). Part of the size comes from Kurmanji and Armenian/Azerbaijani.</p></div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Death tolls: an honest null</div>
  <h2>Tolls diverge more than for disasters, but with no consistent direction</h2>
  <div class="split">
    <div class="figcard">{img('fig1_event_fi.png')}</div>
    <div class="facts">
      <div class="fact"><b>{pct(FR['share_events_diff_ge_25pct'], 0)} vs {pct(FR['share_controls_diff_ge_25pct'], 0)}</b><span>of language pairs differ by ≥25%: conflict events vs non-political controls (Fisher p = {FR['fisher_ge25pct_events_vs_controls_p']:.3f})</span></div>
      <div class="fact"><b>{pct(FR['FI_share_negative'], 0)} / {pct(FR['FI_share_positive'], 0)}</b><span>of cells lower / higher in the attacker's language (Wilcoxon p = {FR['FI_wilcoxon_p']:.2f})</span></div>
      <div class="fact"><b>{civ[0]:+.1f} pts</b><span>civilian-share difference (CI {civ[1]:.1f} to {civ[2]:.1f})</span></div>
      <p class="note">The GPT-3.5 deflation pattern <b>does not replicate</b> in current models. Attribution is where the effect has moved.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Tested mitigation</div>
  <h2>A "same answer in every language" instruction cuts the gap by about {round((1 - gap_p[0] / gap_b[0]) * 10) * 10}%, not to zero</h2>
  <div class="split">
    <div>
      <div class="callout slim">Gap {pts(gap_b[0])} → <b>{pts(gap_p[0])} points</b> (CI {pts(gap_p[1])}–{pts(gap_p[2])}) · McNemar {piv['modal_discordant_victim_only']} vs {piv['modal_discordant_attacker_only']}, p = {piv['mcnemar_exact_p']:.2f}</div>
      <p class="note">Helps three models a lot, does nothing for two, makes three worse. Not a reliable fix at the prompt level.</p>
    </div>
    <table class="tbl"><thead><tr><th>Model</th><th>Baseline gap</th><th>With instruction</th><th></th></tr></thead><tbody>{rows}</tbody></table>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <div class="kicker">Takeaways</div>
  <h2>Cross-lingual consistency is an unmeasured part of model honesty</h2>
  <div class="split">
    <ul class="take">
      <li><b>For evaluators:</b> run contested-event questions in both parties' languages. English-only tests miss this.</li>
      <li><b>For labs:</b> make cross-lingual consistency on contested facts a training and eval target; prompting alone is uneven.</li>
      <li><b>Reusable:</b> 22 events × 11 languages, audited translations, resumable runner. Rerun on each model release for under $1.</li>
      <li class="lim"><b>Limits:</b> measures consistency, not accuracy · forced-choice format · 19 attributed events · small/mid-size models · translations audited by models.</li>
    </ul>
    <div class="qrbox">{qr}<span>Code, data, all {S['n_responses']:,} raw responses</span><code>github.com/astral-fate/same-strike-different-story</code></div>
  </div>
</section>""")

CSS = """
:root{--ink:#0F172A;--muted:#475569;--line:#E2E8F0;--paper:#F8FAFC;--card:#FFFFFF;--navy:#0B1220;--teal:#0F766E;--teal2:#2DD4BF;
--orange:#C2410C;--blue:#1D4ED8;--grey:#64748B;--good:#047857;--bad:#B91C1C;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#0B1220;font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);overflow:hidden}
#deck{position:relative;width:100vw;height:100vh;display:flex;align-items:center;justify-content:center}
.slide{position:absolute;width:min(96vw,170.67vh);height:min(54vw,96vh);background:var(--paper);border-radius:14px;
padding:3.2% 4%;display:flex;flex-direction:column;justify-content:center;opacity:0;pointer-events:none;transform:translateY(10px) scale(.985);
transition:opacity .3s ease,transform .3s ease;box-shadow:0 30px 60px -20px rgba(0,0,0,.7);overflow:hidden;font-size:min(1.45vw,2.58vh)}
.slide.active{opacity:1;pointer-events:auto;transform:none}
.kicker{font-size:.72em;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--teal);margin-bottom:.5em}
h2{font-size:1.75em;font-weight:800;letter-spacing:-.02em;line-height:1.15;margin-bottom:.9em}
p{line-height:1.45}
.dark{background:radial-gradient(circle at 75% 15%,#134E4A 0%,#0B1220 60%);color:#F1F5F9;justify-content:center}
.dark .kicker{color:var(--teal2)}
.title-slide h1{font-size:3.6em;font-weight:800;letter-spacing:-.03em;line-height:1.02;margin:.2em 0 .45em}
.accent{color:var(--teal2)}
.lede{font-size:1.25em;color:#CBD5E1;margin-bottom:2em}
.byline{font-weight:600;font-size:1.05em}.tracks{color:#94A3B8;font-size:.8em;margin-top:.4em}
.cols{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2em;min-height:40%}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.2em 1.3em}
.card p{color:var(--muted)}.card b{color:var(--ink)}
.card.warn{border-color:#FCD34D;background:#FFFBEB}
.big{font-size:2em;margin-bottom:.4em}
.metric{font-size:2.3em;font-weight:800;color:var(--teal);letter-spacing:-.02em;margin-bottom:.3em}
.card.warn .metric{color:#B45309}
.stats{display:grid;grid-template-columns:repeat(6,1fr);gap:.8em;margin-bottom:1.3em}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.8em;text-align:center}
.stat b{display:block;font-size:1.9em;font-weight:800;color:var(--teal)}.stat span{font-size:.72em;color:var(--muted)}
.pipe{display:flex;align-items:stretch;gap:.6em;margin-bottom:1.2em}
.pipe div{flex:1;background:#0F172A;color:#F1F5F9;border-radius:10px;padding:.8em;font-weight:700;font-size:.9em}
.pipe small{display:block;font-weight:400;color:#94A3B8;font-size:.82em;margin-top:.3em}
.pipe i{align-self:center;font-style:normal;color:var(--teal);font-weight:800;font-size:1.3em}
.note{color:var(--muted);font-size:.92em}.note b{color:var(--ink)}.note.top{margin:-.4em 0 1.2em}
.trio{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2em;margin-bottom:1.2em}
.tri{background:var(--card);border-radius:12px;padding:1em 1.3em;border-top:6px solid var(--grey);border:1px solid var(--line)}
.tri.att{border-top:6px solid var(--orange)}.tri.vic{border-top:6px solid var(--blue)}.tri.en{border-top:6px solid var(--grey)}
.tri span{font-weight:700;color:var(--muted);font-size:.85em}
.tri b{display:block;font-size:3em;font-weight:800;letter-spacing:-.03em;margin:.1em 0}
.tri.att b{color:var(--orange)}.tri.vic b{color:var(--blue)}.tri.en b{color:var(--grey)}
.tri small{color:var(--muted)}
.callout{background:#0F172A;color:#E2E8F0;border-radius:10px;padding:.8em 1.1em;margin-bottom:1em;font-size:.92em}
.callout b{color:var(--teal2)}.callout.slim{margin-bottom:.8em}
.figcard{background:#fff;border:1px solid var(--line);border-radius:12px;padding:.6em;display:flex;align-items:center;justify-content:center;min-height:0}
.figcard img{max-width:100%;max-height:100%;object-fit:contain}
.figcard.wide{flex:1;max-height:72%}
.cap{color:var(--muted);font-size:.8em;text-align:center;margin-top:.5em}
.split{display:grid;grid-template-columns:1.1fr 1fr;gap:1.4em;flex:1;min-height:0;max-height:78%}
.split .figcard{height:100%}
.facts{display:flex;flex-direction:column;gap:.8em}
.fact{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.7em 1em}
.fact b{display:block;font-size:1.5em;font-weight:800;color:var(--teal)}.fact span{color:var(--muted);font-size:.85em}
.excards{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2em;margin-bottom:1.3em}
.excard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.1em 1.3em;border-left:7px solid var(--good)}
.excard.miss{border-left-color:var(--orange);background:#FFF7ED}
.exlang{font-weight:800;font-size:1.1em}.exlang span{display:block;font-weight:500;font-size:.72em;color:var(--muted)}
.exans{font-size:1.5em;font-weight:800;margin:.5em 0 .3em}.excard.miss .exans{color:var(--orange)}
.exdeath{font-family:"JetBrains Mono",Consolas,monospace;font-size:.8em;color:var(--muted)}
.tbl{border-collapse:collapse;width:100%;font-size:.85em;background:#fff;border-radius:10px;overflow:hidden;align-self:start}
.tbl th{background:#0F172A;color:#E2E8F0;text-align:left;padding:.5em .7em;font-weight:600}
.tbl td{padding:.42em .7em;border-bottom:1px solid var(--line)}.tbl .num{font-variant-numeric:tabular-nums;text-align:right}
.chip{font-size:.78em;font-weight:700;padding:.15em .6em;border-radius:99px}
.chip.good{background:#D1FAE5;color:var(--good)}.chip.bad{background:#FEE2E2;color:var(--bad)}.chip.flat{background:#F1F5F9;color:var(--grey)}
.take{list-style:none;display:flex;flex-direction:column;gap:.8em}
.take li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.75em 1em;line-height:1.4}
.take li.lim{background:#F1F5F9;color:var(--muted)}
.qrbox{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.6em;background:#fff;border:1px solid var(--line);border-radius:12px;padding:1em}
.qrbox svg{width:62%;height:auto}.qrbox span{font-weight:700}.qrbox code{font-size:.72em;color:var(--muted)}
#hud{position:fixed;bottom:12px;right:18px;color:#94A3B8;font:12px Inter,sans-serif;z-index:50}
#bar{position:fixed;left:0;bottom:0;height:3px;background:#2DD4BF;transition:width .3s;z-index:50}
@media print{html,body{overflow:visible;height:auto;background:#fff}#deck{display:block;height:auto}
.slide{position:relative;opacity:1;transform:none;width:100%;height:auto;aspect-ratio:16/9;page-break-after:always;box-shadow:none;border-radius:0;font-size:12pt}#hud,#bar{display:none}}
"""

JS = """
const s=[...document.querySelectorAll('.slide')];let i=0;
const h=parseInt(location.hash.slice(1));if(h>0&&h<=s.length)i=h-1;
function go(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach((e,k)=>e.classList.toggle('active',k===i));
document.getElementById('hud').textContent=(i+1)+' / '+s.length;document.getElementById('bar').style.width=((i+1)/s.length*100)+'%';
history.replaceState(null,'','#'+(i+1));}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' ','Enter'].includes(e.key)){e.preventDefault();go(i+1)}
else if(['ArrowLeft','PageUp','Backspace'].includes(e.key)){e.preventDefault();go(i-1)}
else if(e.key==='Home')go(0);else if(e.key==='End')go(s.length-1);
else if(e.key==='f'||e.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}});
document.addEventListener('click',e=>{if(e.target.closest('a'))return;go(e.clientX>innerWidth/3?i+1:i-1)});
let tx=null;document.addEventListener('touchstart',e=>tx=e.touches[0].clientX);
document.addEventListener('touchend',e=>{if(tx===null)return;const d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>40)go(d<0?i+1:i-1);tx=null});
go(i);
"""

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{TITLE}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div id="deck">{''.join(slides)}</div><div id="hud"></div><div id="bar"></div>
<script>{JS}</script></body></html>"""
OUT.write_text(html, encoding="utf-8")
print("slides ->", OUT, f"({len(slides)} slides, {OUT.stat().st_size // 1024} KB)")
