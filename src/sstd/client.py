"""Minimal OpenRouter / Groq chat client. No silent fallbacks: failures raise."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    # Look for .env in the repo, then in parent folders (the sprint folder keeps one).
    for d in [ROOT, *ROOT.parents]:
        f = d / ".env"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))
            return


_load_env()

PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
}

# Models that emit hidden reasoning; we ask for minimal reasoning and allow more tokens.
REASONING_HINT = ("anthropic/claude-haiku-5", "anthropic/claude-sonnet-5", "qwen/qwen3","z-ai/glm", "openai/gpt-5", "openai/gpt-oss", "google/gemini-2.5", "google/gemini-3")


def split_model(spec: str) -> tuple[str, str]:
    """'groq:openai/gpt-oss-120b' -> ('groq', 'openai/gpt-oss-120b'); default provider openrouter."""
    if ":" in spec and spec.split(":", 1)[0] in PROVIDERS:
        p, m = spec.split(":", 1)
        return p, m
    return "openrouter", spec


class APIError(RuntimeError):
    pass


def chat(model_spec: str, messages: list[dict], temperature: float = 0.7, max_tokens: int = 200,
         retries: int = 5, timeout: int = 90) -> dict:
    """Returns {'text', 'usage', 'model'}; raises APIError after retries."""
    provider, model = split_model(model_spec)
    url, key_name = PROVIDERS[provider]
    key = os.environ.get(key_name)
    if not key:
        raise APIError(f"missing {key_name}")
    reasoning = model.startswith(REASONING_HINT)
    payload = {"model": model, "messages": messages, "temperature": temperature,
               "max_tokens": max(max_tokens * 6, 3000) if reasoning else max_tokens}
    if reasoning and provider == "openrouter":
        payload["reasoning"] = {"effort": "low", "exclude": True}
    if reasoning and provider == "groq":
        payload["reasoning_effort"] = "low"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "X-Title": "SSDT-epistemics-sprint"}
    delay = 3.0
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                time.sleep(delay); delay = min(delay * 2, 60); continue
            if r.status_code != 200:
                raise APIError(f"HTTP {r.status_code}: {r.text[:300]}")
            js = r.json()
            if "choices" not in js:
                last = f"no choices: {str(js)[:200]}"
                time.sleep(delay); delay *= 2; continue
            ch = js["choices"][0]
            text = (ch["message"].get("content") or "").strip()
            if ch.get("finish_reason") == "length" and not text:
                raise APIError("truncated with no visible output (reasoning budget exhausted)")
            return {"text": text, "usage": js.get("usage", {}), "model": js.get("model", model),
                    "finish_reason": ch.get("finish_reason")}
        except requests.RequestException as e:
            last = repr(e)
            time.sleep(delay); delay = min(delay * 2, 60)
    raise APIError(f"{model_spec}: gave up after {retries} attempts: {last}")
