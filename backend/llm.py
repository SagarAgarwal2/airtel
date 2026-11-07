"""Thin, optional LLM client (Gemini, OpenAI or Anthropic) over plain HTTPS.

Set ONE of GEMINI_API_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY. LLM_MODEL overrides
the default model. With no key the advisor runs on its built-in rule-based parser.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Optional

TIMEOUT = 25


def provider() -> Optional[str]:
    forced = os.environ.get("LLM_PROVIDER")
    if forced:
        return forced
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def model_name() -> str:
    p = provider()
    default = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini", "anthropic": "claude-haiku-4-5"}.get(p, "")
    return os.environ.get("LLM_MODEL", default)


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def complete(system: str, user: str, json_mode: bool = False) -> Optional[str]:
    p = provider()
    if not p:
        return None
    m = model_name()
    try:
        if p == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={os.environ['GEMINI_API_KEY']}"
            body = {"systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {"temperature": 0.2, **({"responseMimeType": "application/json"} if json_mode else {})}}
            r = _post(url, body, {})
            return r["candidates"][0]["content"]["parts"][0]["text"]
        if p == "openai":
            body = {"model": m, "temperature": 0.2,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            r = _post("https://api.openai.com/v1/chat/completions", body,
                      {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
            return r["choices"][0]["message"]["content"]
        if p == "anthropic":
            body = {"model": m, "max_tokens": 800, "temperature": 0.2, "system": system,
                    "messages": [{"role": "user", "content": user}]}
            r = _post("https://api.anthropic.com/v1/messages", body,
                      {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
            return "".join(b.get("text", "") for b in r["content"])
    except Exception as e:  # network, quota, bad key: fall back silently
        print(f"[llm] {p} call failed: {type(e).__name__}: {str(e)[:200]}")
        return None
    return None


def complete_json(system: str, user: str) -> Optional[dict]:
    txt = complete(system, user, json_mode=True)
    if not txt:
        return None
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
