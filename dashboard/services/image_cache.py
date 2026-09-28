# -*- coding: utf-8 -*-
"""Image cache service (T4/T5).

Thin dashboard-facing facade over ``scripts/image_cache.py``: the cache logic
itself lives next to the generator so the CLI pipeline can use it without the
Flask app, while the dashboard exposes stats/purge helpers and the
``/api/images/cache`` endpoints.
"""
try:
    from scripts.image_cache import (
        cache_dir,
        cache_stats,
        cleanup,
        clear_cache,
        env_value,
        get_cached,
        image_cache_key,
        put_cached,
        ttl_days,
    )
except ImportError:  # scripts/ on sys.path instead of the project root
    from image_cache import (
        cache_dir,
        cache_stats,
        cleanup,
        clear_cache,
        env_value,
        get_cached,
        image_cache_key,
        put_cached,
        ttl_days,
    )

DEFAULT_PROVIDER = "auto"


def provider() -> str:
    """Effective IMAGE_PROVIDER setting ('auto' when unset/unknown)."""
    return (env_value("IMAGE_PROVIDER", DEFAULT_PROVIDER) or DEFAULT_PROVIDER).strip().lower()


def summary() -> dict:
    """Cache state + active provider, ready for the API/UI."""
    stats = cache_stats()
    stats["provider"] = provider()
    return stats


def purge_expired() -> int:
    """Delete only entries past their TTL; returns how many files went away."""
    return cleanup()


def purge_all() -> int:
    """Delete every cached entry; returns how many files went away."""
    return clear_cache()


__all__ = [
    "cache_dir",
    "cache_stats",
    "env_value",
    "get_cached",
    "image_cache_key",
    "provider",
    "purge_all",
    "purge_expired",
    "put_cached",
    "summary",
    "ttl_days",
]
