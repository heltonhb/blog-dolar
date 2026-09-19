# -*- coding: utf-8 -*-
"""Shared helper utilities extracted from app.py."""
import json
import os
import re
import secrets
from functools import wraps
from pathlib import Path

from flask import jsonify, redirect, request, session, url_for


# ---------------------------------------------------------------------------
#  Path helpers
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Return the project root directory (parent of dashboard/)."""
    return Path(__file__).resolve().parent.parent.parent


def _dashboard_dir() -> Path:
    """Return the dashboard/ directory."""
    return Path(__file__).resolve().parent.parent


def _env(key: str, default: str = "") -> str:
    """Safely read an environment variable, falling back to .env file."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        env = _load_env_dict()
        return env.get(key, default)
    except Exception:
        return default


def _data_path(name: str) -> Path:
    """Resolve path inside dashboard/data/."""
    return _dashboard_dir() / "data" / name


def _articles_dir() -> Path:
    """Resolve path to root articles/ directory."""
    return _project_root() / "articles"


def _scripts_dir() -> Path:
    """Resolve path to root scripts/ directory."""
    p = _project_root() / "scripts"
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
    return p


def _images_dir() -> Path:
    """Resolve path to dashboard/static/images directory."""
    p = _dashboard_dir() / "static" / "images"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
#  JSON file helpers
# ---------------------------------------------------------------------------

def _load_json(name: str, default=None):
    """Read and parse JSON file from dashboard/data/."""
    p = _data_path(name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def _save_json(name: str, data):
    """Serialize and write JSON file to dashboard/data/."""
    p = _data_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
#  .env file helpers
# ---------------------------------------------------------------------------

def _load_env_dict() -> dict:
    """Read .env file into dict (checking root .env, then persistent data disk)."""
    env = {}
    paths = [_project_root() / ".env", _data_path(".env")]
    for path in paths:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    return env


def _save_env_dict(env: dict):
    """Overwrite .env file in root and persistent data disk."""
    lines = [f"{k}={v}" for k, v in env.items()]
    content = "\n".join(lines) + "\n"
    _project_root().joinpath(".env").write_text(content, encoding="utf-8")
    try:
        data_env = _data_path(".env")
        data_env.parent.mkdir(parents=True, exist_ok=True)
        data_env.write_text(content, encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
#  JSON parsing (from LLM output)
# ---------------------------------------------------------------------------

def _parse_json(text: str):
    """Extract and decode JSON from LLM markdown fences or bracket matching."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[[\s\S]*\]|\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        raise


# ---------------------------------------------------------------------------
#  Authentication
# ---------------------------------------------------------------------------

def _get_dashboard_password() -> str:
    """Return the dashboard password from env/file (never hardcoded)."""
    pwd = os.environ.get("DASHBOARD_PASSWORD", "")
    if not pwd:
        env = _load_env_dict()
        pwd = env.get("DASHBOARD_PASSWORD", "")
    return pwd


def login_required(f):
    """Decorator: redirect to /login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _get_dashboard_password():
            # No password set -> open mode (backwards compatible)
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Não autenticado"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated
