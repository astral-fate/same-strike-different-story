"""Resumable job runner: each finished job is appended to a JSONL file immediately.
Rerunning skips keys already present with status 'ok' and retries failures."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

_lock = threading.Lock()


def done_keys(path: Path) -> set[str]:
    keys = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # a partially written last line from a crash
            if r.get("status") == "ok":
                keys.add(r["key"])
    return keys


def latest_ok(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok":
                out[r["key"]] = r
    return out


def run_jobs(jobs: list[dict], fn: Callable[[dict], dict], out: Path, log: Path, workers: int = 8) -> None:
    """jobs: dicts with a unique 'key'. fn(job) -> result dict (raise on failure)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    skip = done_keys(out)
    todo = [j for j in jobs if j["key"] not in skip]
    msg = f"{time.strftime('%H:%M:%S')} {out.name}: {len(jobs)} jobs, {len(skip & {j['key'] for j in jobs})} done, {len(todo)} to run"
    print(msg)
    with log.open("a", encoding="utf-8") as lf:
        lf.write(msg + "\n")
    n_ok = n_err = 0

    def work(j):
        try:
            res = fn(j)
            return {**j, **res, "status": "ok", "ts": time.time()}
        except Exception as e:  # recorded, retried on next run
            return {**j, "status": "error", "error": repr(e)[:500], "ts": time.time()}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, j) for j in todo]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            with _lock:
                with out.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                if r["status"] == "ok":
                    n_ok += 1
                else:
                    n_err += 1
                    with log.open("a", encoding="utf-8") as lf:
                        lf.write(f"ERR {r['key']}: {r['error']}\n")
            if i % 50 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} ok={n_ok} err={n_err}", flush=True)
    with log.open("a", encoding="utf-8") as lf:
        lf.write(f"{time.strftime('%H:%M:%S')} {out.name}: finished ok={n_ok} err={n_err}\n")
