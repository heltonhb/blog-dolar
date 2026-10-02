# -*- coding: utf-8 -*-
"""Settings and diagnostic API routes."""
import os
import subprocess
import sys

import httpx
from flask import Blueprint, jsonify, request

from dashboard.services.helpers import (
    _env,
    _load_env_dict,
    _project_root,
    _save_env_dict,
    _scripts_dir,
    login_required,
)
from dashboard.services.wordpress import _antibot_session

settings_bp = Blueprint("settings", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
#  Script runner allowlist
# ---------------------------------------------------------------------------
# The runner used to accept ANY path under scripts/ plus free-form argv, with the
# whole .env (DATABASE_URL, WP_APP_PASSWORD, GOOGLE_REFRESH_TOKEN...) injected
# into the child process. One authenticated request was full remote code
# execution. Only these known, side-effect-bounded maintenance scripts may run,
# and they take NO arguments from the request body.
ALLOWED_SCRIPTS: dict[str, str] = {
    "analytics_ga4.py": "Puxa métricas do GA4 para o cache",
    "analytics_bing.py": "Puxa métricas do Bing Webmaster para o cache",
    "indexnow_submit.py": "Envia URLs ao IndexNow",
    "check_indexacao.py": "Consulta indexação no Google Search Console",
    "check_sitemap_indexacao.py": "Checa o sitemap no Search Console",
    "relatorio_indexacao.py": "Gera relatório de indexação",
    "fetch_wp_post.py": "Baixa um post do WordPress para inspeção",
}


def _is_masked(value: str) -> bool:
    """Return True if the value looks like a masked secret (should not be saved)."""
    if not value:
        return False
    if "..." in value or value == "***" or value.endswith("..."):
        return True
    return False


@settings_bp.route("/settings", methods=["GET"])
@login_required
def api_settings_get():
    """Return environment variables with sensitive secrets masked."""
    env = _load_env_dict()
    masked = {}
    for k, v in env.items():
        if any(s in k for s in ["PASS", "SECRET", "TOKEN", "KEY"]):
            masked[k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "***"
        else:
            masked[k] = v
    return jsonify(masked)


@settings_bp.route("/settings", methods=["POST"])
@login_required
def api_settings_save():
    """Save updated settings to .env file, ignoring masked secret fields."""
    try:
        data = request.json or {}
        env = _load_env_dict()
        skipped = []
        for k, v in data.items():
            if not k:
                continue
            v = (v or "").strip()
            if not v:
                continue
            if _is_masked(v):
                skipped.append(k)
                continue
            env[k] = v

        _save_env_dict(env)
        for k, v in env.items():
            os.environ[k] = v

        result = {"success": True}
        if skipped:
            result["skipped"] = skipped
            result["warning"] = f"Valores mascarados não foram salvos: {', '.join(skipped)}"
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/settings/test_wp", methods=["POST"])
@login_required
def api_test_wp():
    """Test WordPress REST API connection and authentication."""
    try:
        env = _load_env_dict()
        site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
        wp_user = env.get("WP_USER") or _env("WP_USER", "")
        wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

        if not wp_user or not wp_pass:
            return jsonify({"success": False, "error": "Configure WP_USER e WP_APP_PASSWORD"}), 400

        client = _antibot_session(site_url)
        resp = client.get(
            f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me",
            auth=(wp_user, wp_pass),
            timeout=15,
        )
        if resp.status_code == 200:
            user = resp.json()
            return jsonify({"success": True, "message": f"Conectado como: {user.get('name', 'Unknown')}"})
        return jsonify({"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/test-gemini")
@settings_bp.route("/settings/test_gemini", methods=["POST", "GET"])
@login_required
def api_test_gemini():
    """Test Gemini API key validity."""
    api_key = _env("GEMINI_API_KEY", "")
    if not api_key:
        return jsonify({"success": False, "error": "GEMINI_API_KEY não configurada"}), 400

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return jsonify({
                "success": True,
                "key_preview": api_key[:10] + "...",
                "models_count": len(models),
                "status": "OK",
            })
        return jsonify({
            "success": False,
            "error": f"HTTP {resp.status_code}",
            "key_preview": api_key[:10] + "...",
            "detail": resp.text[:200],
        }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/settings/test_pinterest", methods=["POST"])
@login_required
def api_test_pinterest():
    """Test Pinterest API token."""
    access_token = _env("PINTEREST_ACCESS_TOKEN", "")
    if not access_token:
        return jsonify({"success": False, "error": "PINTEREST_ACCESS_TOKEN não configurada"}), 400

    try:
        resp = httpx.get(
            "https://api.pinterest.com/v5/user_account",
            headers={"Authorization": f"Bearer {access_token}" if not access_token.startswith("Bearer ") else access_token},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return jsonify({
                "success": True,
                "username": data.get("username", "Pinterest User"),
                "account_type": data.get("account_type", "BUSINESS"),
            })
        return jsonify({"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/run_script", methods=["POST"])
@login_required
def api_run_script():
    """Execute one allow-listed maintenance script from scripts/ (no argv)."""
    script_name = (request.json or {}).get("script_name", "") or ""

    # Bare filename only: no separators, no traversal, no absolute paths.
    if not script_name or "/" in script_name or "\\" in script_name or ".." in script_name:
        return jsonify({
            "success": False,
            "error": "script_name inválido: use apenas o nome do arquivo",
        }), 400

    if script_name not in ALLOWED_SCRIPTS:
        return jsonify({
            "success": False,
            "error": f"Script não permitido: {script_name}",
            "allowed": sorted(ALLOWED_SCRIPTS),
        }), 403

    # Resolve and confirm the target really is a file inside scripts/.
    scripts_root = _scripts_dir().resolve()
    script_path = (scripts_root / script_name).resolve()
    if not script_path.is_relative_to(scripts_root) or not script_path.is_file():
        return jsonify({"success": False, "error": "Script não encontrado"}), 404

    venv_python = _project_root() / "venv" / "bin" / "python"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    env = os.environ.copy()
    env.update(_load_env_dict())

    try:
        # No argv from the request: the script runs with its own defaults.
        result = subprocess.run(
            [python_bin, str(script_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(scripts_root.parent),
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "output": "Timeout: script demorou mais de 5 minutos"}), 504
    except Exception as e:
        return jsonify({"success": False, "output": str(e)}), 500

    return jsonify({
        "success": result.returncode == 0,
        "output": (result.stdout or "") + ("\n" + result.stderr if result.stderr else ""),
    })


@settings_bp.route("/run_script/allowed", methods=["GET"])
@login_required
def api_run_script_allowed():
    """List the scripts the runner is permitted to execute."""
    return jsonify({
        "success": True,
        "allowed": [{"name": n, "description": d} for n, d in sorted(ALLOWED_SCRIPTS.items())],
    })
