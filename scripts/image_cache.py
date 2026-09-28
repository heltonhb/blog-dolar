#!/usr/bin/env python3
"""
Blog em Dolar - Image cache (TTL)

Caches generated images in ``cache/images/`` keyed by a SHA-256 hash of the
prompt (plus usage + provider). Repeated pipeline runs / retries / previews
then cost zero API calls and stay visually consistent.

Design notes:
- TTL comes from the file mtime, so no metadata bookkeeping is required
  (a ``.json`` sidecar is written only for observability).
- Expired files are removed lazily on read and by an hourly throttled sweep
  (``_maybe_cleanup``) triggered on every read/write.
- Override the location with ``IMAGE_CACHE_DIR`` (used by the tests) and the
  TTL with ``IMAGE_CACHE_TTL_DAYS`` (default 7).

Stdlib only — importable from the CLI pipeline (``scripts/``) and from the
dashboard (``dashboard/services/image_cache.py`` facade).
"""
import hashlib
import json
import os
import time
from pathlib import Path

DEFAULT_TTL_DAYS = 7.0
_CLEANUP_INTERVAL_SECONDS = 3600
_last_cleanup = 0.0


def env_value(key: str, default: str = "") -> str:
    """os.environ first, then the project .env files (CLI has no load_dotenv)."""
    val = os.environ.get(key)
    if val:
        return val
    root = Path(__file__).resolve().parent.parent
    for path in (root / ".env", root / "dashboard" / "data" / ".env"):
        try:
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        if k.strip() == key:
                            return v.strip()
        except OSError:
            continue
    return default


def cache_dir() -> Path:
    """Directory holding cached images (created on demand)."""
    override = env_value("IMAGE_CACHE_DIR", "")
    path = Path(override).expanduser() if override else (
        Path(__file__).resolve().parent.parent / "cache" / "images"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def ttl_days() -> float:
    try:
        return max(0.0, float(env_value("IMAGE_CACHE_TTL_DAYS", "") or DEFAULT_TTL_DAYS))
    except ValueError:
        return DEFAULT_TTL_DAYS


def ttl_seconds() -> float:
    return ttl_days() * 86400


def image_cache_key(prompt: str, usage: str = "", provider: str = "") -> str:
    """Stable cache key: hash of usage + provider + prompt."""
    raw = f"{usage.strip().lower()}\x00{provider.strip().lower()}\x00{prompt.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _image_path(key: str, directory: "Path | None" = None) -> Path:
    return (directory or cache_dir()) / f"{key}.img"


def _meta_path(key: str, directory: "Path | None" = None) -> Path:
    return (directory or cache_dir()) / f"{key}.json"


def get_cached(key: str, directory: "Path | None" = None, now: "float | None" = None) -> "bytes | None":
    """Return cached image bytes, or None when missing/expired.

    Expired entries are deleted on sight (lazy cleanup).
    """
    now = time.time() if now is None else now
    path = _image_path(key, directory)
    try:
        stat = path.stat()
    except OSError:
        return None

    if now - stat.st_mtime > ttl_seconds():
        _unlink_quiet(path)
        _unlink_quiet(_meta_path(key, directory))
        return None

    try:
        return path.read_bytes()
    except OSError:
        return None


def put_cached(
    key: str,
    data: bytes,
    directory: "Path | None" = None,
    meta: "dict | None" = None,
) -> "Path | None":
    """Store image bytes atomically (write to .tmp, then rename). Returns the path."""
    if not data:
        return None
    directory = directory or cache_dir()
    path = _image_path(key, directory)
    tmp = path.with_suffix(".tmp")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        tmp.replace(path)

        payload = {
            "size": len(data),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "ttl_days": ttl_days(),
        }
        if meta:
            payload.update(meta)
        _meta_path(key, directory).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        return None

    _maybe_cleanup(directory)
    return path


def cleanup(directory: "Path | None" = None, now: "float | None" = None, ttl: "float | None" = None) -> int:
    """Delete expired cache entries; returns how many files were removed."""
    directory = directory or cache_dir()
    now = time.time() if now is None else now
    ttl = ttl_seconds() if ttl is None else ttl
    removed = 0
    try:
        entries = list(directory.iterdir())
    except OSError:
        return 0

    for entry in entries:
        try:
            expired = now - entry.stat().st_mtime > ttl
        except OSError:
            continue
        if expired and entry.suffix in (".img", ".json", ".tmp"):
            if _unlink_quiet(entry):
                removed += 1
    return removed


def _maybe_cleanup(directory: "Path | None" = None, now: "float | None" = None) -> int:
    """Throttled sweep: at most once per _CLEANUP_INTERVAL_SECONDS."""
    global _last_cleanup
    now = time.time() if now is None else now
    if now - _last_cleanup < _CLEANUP_INTERVAL_SECONDS:
        return 0
    _last_cleanup = now
    return cleanup(directory, now=now)


def clear_cache(directory: "Path | None" = None) -> int:
    """Remove every cached entry; returns the number of files deleted."""
    directory = directory or cache_dir()
    removed = 0
    try:
        entries = list(directory.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if entry.suffix in (".img", ".json", ".tmp") and _unlink_quiet(entry):
            removed += 1
    return removed


def cache_stats(directory: "Path | None" = None, now: "float | None" = None) -> dict:
    """Human/JSON friendly summary of the cache state."""
    directory = directory or cache_dir()
    now = time.time() if now is None else now
    files = 0
    total_bytes = 0
    oldest = None
    newest = None
    try:
        for entry in directory.glob("*.img"):
            stat = entry.stat()
            files += 1
            total_bytes += stat.st_size
            oldest = stat.st_mtime if oldest is None else min(oldest, stat.st_mtime)
            newest = stat.st_mtime if newest is None else max(newest, stat.st_mtime)
    except OSError:
        pass

    return {
        "dir": str(directory),
        "files": files,
        "size_mb": round(total_bytes / 1048576, 2),
        "ttl_days": ttl_days(),
        "expired": sum(
            1 for entry in directory.glob("*.img")
            if _is_expired(entry, now)
        ) if directory.exists() else 0,
        "oldest": time.strftime("%Y-%m-%d %H:%M", time.localtime(oldest)) if oldest else None,
        "newest": time.strftime("%Y-%m-%d %H:%M", time.localtime(newest)) if newest else None,
    }


def _is_expired(path: Path, now: float) -> bool:
    try:
        return now - path.stat().st_mtime > ttl_seconds()
    except OSError:
        return False


def _unlink_quiet(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except OSError:
        return False
