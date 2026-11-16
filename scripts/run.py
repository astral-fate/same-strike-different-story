"""Step 2: query every model x condition x (item, language) cell x sample. Resumable.
Usage: python scripts/run.py [--models m1,m2] [--samples 3] [--pilot]"""
from __future__ import annotations

import argparse
import random
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sstd.client import chat  # noqa: E402
from sstd.items import CONDITIONS  # noqa: E402
from sstd.jobs import run_jobs  # noqa: E402
from sstd.parse import parse_answer  # noqa: E402

MODELS = [
    "openai/gpt-4o-mini",                         # US, closed
    "anthropic/claude-haiku-5.5",                 # US, closed, current generation
    "deepseek/deepseek-chat",                     # CN, open weights
    "qwen/qwen3.7-flash",                         # CN, current generation
    "z-ai/glm-5.3-flash",                         # CN
    "mistralai/mistral-small-24b-instruct-2501",  # EU, open weights
    "meta-llama/llama-3.1-8b-instruct",           # US, open weights, small
    "openai/gpt-5.6-luna",                        # US, closed, current generation
]
TEMPERATURE = 0.7


def call(job):
    msgs = []
    if CONDITIONS[job["condition"]]:
        msgs.append({"role": "system", "content": CONDITIONS[job["condition"]]})
    msgs.append({"role": "user", "content": job["prompt"]})
    r = chat(job["model"], msgs, temperature=TEMPERATURE, max_tokens=120)
    return {"response": r["text"], "finish_reason": r.get("finish_reason"),
            "cost": (r["usage"] or {}).get("cost"), **parse_answer(r["text"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--pilot", action="store_true", help="2 events + 1 control, 1 sample, baseline only")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    prompts = [json.loads(l) for l in (ROOT / "data" / "prompts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.pilot:
        prompts = [p for p in prompts if p["item"] in ("il_ahli", "ru_kramatorsk", "ctl_titanic")]
    conds = ["baseline"] if a.pilot else list(CONDITIONS)
    samples = 1 if a.pilot else a.samples
    jobs = []
    for m in a.models.split(","):
        for c in conds:
            for p in prompts:
                for s in range(samples):
                    jobs.append({"key": f"{m}|{c}|{p['item']}|{p['lang']}|{s}", "model": m, "condition": c,
                                 "item": p["item"], "kind": p["kind"], "conflict": p["conflict"],
                                 "lang": p["lang"], "sample": s, "prompt": p["prompt"]})
    random.Random(0).shuffle(jobs)  # interleave models so slow reasoning models run in parallel
    out = ROOT / "results" / ("pilot.jsonl" if a.pilot else "runs.jsonl")
    run_jobs(jobs, call, out, ROOT / "results" / "run.log", workers=a.workers)


if __name__ == "__main__":
    main()
