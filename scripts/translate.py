"""Step 1: translate every English source prompt, back-translate with a different model lineage,
and audit equivalence + neutrality. Output: data/prompts.jsonl (frozen prompt set) and results/translation_audit.jsonl."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sstd.client import chat  # noqa: E402
from sstd.items import LANG_NAMES, cells  # noqa: E402
from sstd.jobs import latest_ok, run_jobs  # noqa: E402

TRANSLATOR = "anthropic/claude-haiku-5.5"
BACK = "openai/gpt-4o-mini"
AUDITOR = "openai/gpt-4o-mini"

T_SYS = """You are a professional translator preparing a multilingual survey instrument.
Translate the user's text into {lang}. Rules:
- Faithful and neutral: do not add, remove or soften anything; avoid politically loaded terms the source does not use.
- Keep the labels DEATHS:, CIVILIAN_PERCENT:, RESPONSIBLE: exactly as written in Latin letters, and keep the option letters A) B) C) D) and placeholders like <number> unchanged.
- For each place name, write the usual form in {lang} followed by the English spelling in parentheses, once.
- Output only the translation, nothing else."""


def translate(job):
    lang = LANG_NAMES[job["lang"]]
    tr = chat(TRANSLATOR, [{"role": "system", "content": T_SYS.format(lang=lang)},
                           {"role": "user", "content": job["en_prompt"]}], temperature=0, max_tokens=700)
    t = tr["text"]
    if not t or tr.get("finish_reason") == "length":
        raise RuntimeError(f"translation empty or truncated (finish={tr.get('finish_reason')})")
    b = chat(BACK, [{"role": "system", "content": (
        "You are a translator. The text inside <source> tags is a survey question written in another language. "
        "Translate the WHOLE text into English literally, line by line, keeping labels and placeholders. "
        "Do NOT answer the question. Output only the English translation.")},
                    {"role": "user", "content": f"<source>\n{t}\n</source>"}], temperature=0, max_tokens=700)["text"]
    b = b.replace("<source>", "").replace("</source>", "").strip()
    if not b:
        raise RuntimeError("empty back-translation")
    back_ok = "DEATHS:" in b and len(b) > 0.6 * len(job["en_prompt"]) and "<number>" in b
    audit_prompt = f"""Compare an ORIGINAL English survey question with a BACK-TRANSLATION of its {lang} version.
ORIGINAL:
{job['en_prompt']}

BACK-TRANSLATION:
{b}

Return JSON only: {{"equivalent": true/false (same event, same questions, same answer options and labels), "loaded": true/false (the back-translation uses evaluative or partisan wording absent from the original, e.g. massacre, terrorist, martyr, liberation, genocide), "note": "<short>"}}"""
    a = chat(AUDITOR, [{"role": "user", "content": audit_prompt}], temperature=0, max_tokens=150)["text"]
    try:
        aj = json.loads(a[a.index("{"): a.rindex("}") + 1])
    except ValueError:
        raise RuntimeError(f"unparseable audit: {a[:200]}")
    labels_ok = "DEATHS:" in t and (job["kind"] == "control" or ("RESPONSIBLE:" in t and "CIVILIAN_PERCENT:" in t))
    return {"prompt": t, "back": b, "equivalent": bool(aj.get("equivalent")) and back_ok, "loaded": bool(aj.get("loaded")),
            "audit_note": aj.get("note", ""), "labels_ok": labels_ok}


def main():
    jobs = []
    for c in cells():
        if c["lang"] == "en":
            continue
        jobs.append({**c, "key": f"{c['item']}|{c['lang']}"})
    out = ROOT / "results" / "translation_audit.jsonl"
    run_jobs(jobs, translate, out, ROOT / "results" / "run.log", workers=8)

    done = latest_ok(out)
    prompts = []
    for c in cells():
        if c["lang"] == "en":
            prompts.append({**c, "prompt": c["en_prompt"]})
        else:
            r = done.get(f"{c['item']}|{c['lang']}")
            if r:
                prompts.append({**c, "prompt": r["prompt"]})
    (ROOT / "data" / "prompts.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in prompts) + "\n", encoding="utf-8")
    bad = [k for k, r in done.items() if not (r["equivalent"] and r["labels_ok"]) or r["loaded"]]
    print(f"prompts.jsonl: {len(prompts)} cells; flagged for review: {len(bad)} -> {bad}")


if __name__ == "__main__":
    main()
