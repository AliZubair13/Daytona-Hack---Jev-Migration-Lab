"""Host-side provider clients (Jev, Groq). Keys stay on the host; nothing here runs in a sandbox."""
import json
import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
load_env(ROOT / "_env")


class ProviderError(RuntimeError):
    pass


def jev_call(state: dict, questions: dict, timeout: float = 60.0) -> dict:
    """POST /v1/systemone. Returns {answers, usage, ms, model}."""
    key = os.environ.get("JEV_API_KEY")
    if not key:
        raise ProviderError("JEV_API_KEY not set")
    base = os.environ.get("JEV_BASE_URL", "https://api.typesafe.ai").rstrip("/")
    body = {"model": os.environ.get("JEV_MODEL", "jev-latest"), "state": state, "questions": questions}
    t0 = time.perf_counter()
    r = httpx.post(f"{base}/v1/systemone", json=body,
                   headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        raise ProviderError(f"Jev HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    return {"answers": data.get("answers", {}), "usage": data.get("usage", {}),
            "model": data.get("model"), "ms": round(ms, 1)}


def groq_chat(messages: list, model: str | None = None, json_mode: bool = False,
              timeout: float = 60.0) -> dict:
    """OpenAI-compatible Groq chat call. Returns {text, usage, ms, model}."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise ProviderError("GROQ_API_KEY not set")
    model = model or os.environ.get("GROQ_MODEL", "allam-2-7b")
    body = {"model": model, "messages": messages, "temperature": 0}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    for attempt in range(4):
        t0 = time.perf_counter()
        r = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=body,
                       headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 429:
            time.sleep(float(r.headers.get("retry-after", 5)) + 1)
            continue
        if r.status_code != 200:
            raise ProviderError(f"Groq HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        return {"text": data["choices"][0]["message"]["content"], "usage": data.get("usage", {}),
                "model": model, "ms": round(ms, 1)}
    raise ProviderError("Groq rate-limited after retries")


if __name__ == "__main__":
    print(json.dumps({k: bool(os.environ.get(k)) for k in
                      ["JEV_API_KEY", "GROQ_API_KEY", "DAYTONA_API_KEY", "ARIZE_API_KEY"]}, indent=2))
