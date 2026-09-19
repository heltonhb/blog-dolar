# -*- coding: utf-8 -*-
"""Gemini AI integration."""
import os

from .helpers import _env


def _gemini_call(prompt: str, api_key: str = "", model: str = "",
                 temperature: float = 0.7, max_tokens: int = 8192) -> str:
    """Call Gemini API with model fallbacks and retries."""
    import httpx
    import time as _time

    api_key = api_key or _env("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada")

    models = [model] if model else []
    models += ["gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash-lite"]
    models = list(dict.fromkeys(models))

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    last_err = None
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        for attempt in range(3):
            try:
                with httpx.Client(timeout=90) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code in (503, 429):
                        _time.sleep(5 * (attempt + 1))
                        last_err = f"HTTP {resp.status_code}"
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_err = str(e)
                _time.sleep(3 * (attempt + 1))
        print(f"  ⚠️ Modelo {m} falhou, tentando próximo...")
    raise RuntimeError(f"Falha Gemini: todos os modelos indisponíveis. Erro: {last_err}")
