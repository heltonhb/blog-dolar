# -*- coding: utf-8 -*-
"""Tests for the image cache (T5) and IMAGE_PROVIDER selection (T4)."""
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import image_cache  # noqa: E402
import image_generator  # noqa: E402


IMG = b"\x89PNG" + b"x" * 8192  # > 5000 bytes, like a real generated image


@pytest.fixture
def cdir(tmp_path, monkeypatch):
    """Point the cache at a temp directory for the whole test."""
    d = tmp_path / "cache_images"
    monkeypatch.setenv("IMAGE_CACHE_DIR", str(d))
    monkeypatch.setenv("IMAGE_CACHE_TTL_DAYS", "7")
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    return d


# ---------------------------------------------------------------------------
#  Keys / TTL
# ---------------------------------------------------------------------------

def test_cache_key_is_stable_and_scoped():
    a = image_cache.image_cache_key("a red cube", "square", "pollinations")
    b = image_cache.image_cache_key("a red cube", "square", "pollinations")
    assert a == b and len(a) == 64
    assert a != image_cache.image_cache_key("a blue cube", "square", "pollinations")
    assert a != image_cache.image_cache_key("a red cube", "pinterest", "pollinations")
    assert a != image_cache.image_cache_key("a red cube", "square", "gemini-imagen")


def test_ttl_comes_from_env(monkeypatch):
    monkeypatch.setenv("IMAGE_CACHE_TTL_DAYS", "3")
    assert image_cache.ttl_days() == 3
    monkeypatch.setenv("IMAGE_CACHE_TTL_DAYS", "não-número")
    assert image_cache.ttl_days() == image_cache.DEFAULT_TTL_DAYS


def test_put_get_roundtrip(cdir):
    key = image_cache.image_cache_key("prompt", "square", "pollinations")
    path = image_cache.put_cached(key, IMG, meta={"provider": "pollinations"})
    assert path is not None and path.exists()
    assert image_cache.get_cached(key) == IMG
    # sidecar metadata for observability
    meta = (cdir / f"{key}.json").read_text(encoding="utf-8")
    assert "pollinations" in meta


def test_expired_entry_is_dropped(cdir):
    key = image_cache.image_cache_key("old prompt", "square", "pollinations")
    path = image_cache.put_cached(key, IMG)
    # age the file beyond the 7-day TTL
    old = time.time() - (8 * 86400)
    os.utime(path, (old, old))

    assert image_cache.get_cached(key) is None
    assert not path.exists()
    assert not (cdir / f"{key}.json").exists()


def test_cleanup_keeps_fresh_removes_expired(cdir):
    fresh_key = image_cache.image_cache_key("fresh", "square", "pollinations")
    stale_key = image_cache.image_cache_key("stale", "square", "pollinations")
    fresh = image_cache.put_cached(fresh_key, IMG)
    stale = image_cache.put_cached(stale_key, IMG)
    old = time.time() - (10 * 86400)
    os.utime(stale, (old, old))

    removed = image_cache.cleanup()
    assert removed >= 1
    assert fresh.exists() and not stale.exists()


def test_stats_and_clear(cdir):
    key = image_cache.image_cache_key("stats prompt", "square", "pollinations")
    image_cache.put_cached(key, IMG)

    stats = image_cache.cache_stats()
    assert stats["files"] == 1
    assert stats["size_mb"] > 0
    assert stats["ttl_days"] == 7
    assert stats["expired"] == 0

    assert image_cache.clear_cache() == 2  # .img + .json
    assert image_cache.cache_stats()["files"] == 0


# ---------------------------------------------------------------------------
#  IMAGE_PROVIDER ordering (T4)
# ---------------------------------------------------------------------------

def test_auto_order_prefers_available_defaults():
    chain = image_generator._provider_chain("auto", ["gemini-imagen", "pollinations"])
    assert chain == ["gemini-imagen", "pollinations"]


def test_explicit_provider_goes_first():
    chain = image_generator._provider_chain(
        "pollinations", ["together-flux", "gemini-imagen", "pollinations"]
    )
    assert chain == ["pollinations", "together-flux", "gemini-imagen"]


def test_huggingface_only_when_available():
    assert image_generator._provider_chain("huggingface", ["pollinations"]) == ["pollinations"]
    chain = image_generator._provider_chain("huggingface", ["huggingface", "gemini-imagen", "pollinations"])
    assert chain[0] == "huggingface"
    assert "pollinations" in chain


def test_unknown_value_falls_back_to_auto():
    assert image_generator._normalize_provider("provedor-inventado") == "auto"
    chain = image_generator._provider_chain("provedor-inventado", ["gemini-imagen", "pollinations"])
    assert chain == ["gemini-imagen", "pollinations"]


def test_provider_callers_respect_keys(monkeypatch):
    monkeypatch.setattr(image_generator, "env_value", lambda k, d="": d)
    callers = image_generator._provider_callers(api_key="", usage="square")
    assert list(callers) == ["pollinations"]  # no optional keys -> free fallback only

    callers = image_generator._provider_callers(api_key="fake-key", usage="square")
    assert "gemini-imagen" in callers and "pollinations" in callers


# ---------------------------------------------------------------------------
#  generate_image x cache integration
# ---------------------------------------------------------------------------

def _force_provider(monkeypatch, preferred: str):
    """Isolate generate_image from the developer's .env (keys/IMAGE_PROVIDER)."""
    monkeypatch.setattr(
        image_generator,
        "env_value",
        lambda k, d="": preferred if k == "IMAGE_PROVIDER" else d,
    )


def test_generate_image_hits_cache_without_network(cdir, monkeypatch):
    prompt = "a red cube on a desk, studio lighting"
    key = image_cache.image_cache_key(prompt, "square", "pollinations")
    image_cache.put_cached(key, IMG, meta={"provider": "pollinations"})

    def _no_network(*args, **kwargs):
        raise AssertionError("provider should not be called on a cache hit")

    _force_provider(monkeypatch, "pollinations")
    monkeypatch.setattr(image_generator, "generate_image_pollinations", _no_network)

    data, provider = image_generator.generate_image(prompt, api_key="", usage="square")
    assert data == IMG
    assert provider == "pollinations"


def test_generate_image_writes_cache(cdir, monkeypatch):
    prompt = "a blue cube on a desk, studio lighting"
    _force_provider(monkeypatch, "pollinations")
    monkeypatch.setattr(
        image_generator,
        "generate_image_pollinations",
        lambda *a, **k: IMG,
    )

    data, provider = image_generator.generate_image(prompt, api_key="", usage="square")
    assert data == IMG
    assert provider == "pollinations"

    key = image_cache.image_cache_key(prompt, "square", "pollinations")
    assert image_cache.get_cached(key) == IMG

    # second call is served from the cache even if the provider dies
    monkeypatch.setattr(
        image_generator,
        "generate_image_pollinations",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    data2, provider2 = image_generator.generate_image(prompt, api_key="", usage="square")
    assert data2 == IMG and provider2 == "pollinations"


# ---------------------------------------------------------------------------
#  API endpoints
# ---------------------------------------------------------------------------

def test_cache_endpoints(client, cdir):
    resp = client.get("/api/images/cache")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["ttl_days"] == 7
    assert "provider" in data and "files" in data

    resp = client.delete("/api/images/cache?expired=1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["scope"] == "expired"


def test_images_page_shows_cache_ui(client):
    resp = client.get("/images")
    assert resp.status_code == 200
    assert b"cache-badge" in resp.data
    assert b"loadCacheInfo" in resp.data


def test_image_provider_env_selects_first_choice(cdir, monkeypatch):
    _force_provider(monkeypatch, "pollinations")
    callers = image_generator._provider_callers(api_key="fake-key", usage="square")
    chain = image_generator._provider_chain("pollinations", list(callers))
    assert chain == ["pollinations", "gemini-imagen"]  # preferred first, fallback kept
