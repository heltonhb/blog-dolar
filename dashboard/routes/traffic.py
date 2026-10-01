# -*- coding: utf-8 -*-
"""Traffic and Analytics API routes (GA4, Search Console, Pinterest referral metrics)."""
import subprocess
import sys
from flask import Blueprint, jsonify

from dashboard.services.helpers import _load_json, _scripts_dir, login_required

traffic_bp = Blueprint("traffic", __name__, url_prefix="/api/traffic")


@traffic_bp.route("/ga4")
@login_required
def api_traffic_ga4():
    """Return cached GA4 sessions by origin source."""
    return jsonify(_load_json("analytics_source.json", {
        "success": False,
        "error": "sem dados ainda",
    }))


@traffic_bp.route("/ga4/refresh", methods=["POST"])
@login_required
def api_traffic_ga4_refresh():
    """Execute scripts/analytics_ga4.py to pull live GA4 analytics into cache."""
    try:
        script = _scripts_dir() / "analytics_ga4.py"
        if not script.exists():
            return jsonify({"success": False, "error": "script analytics_ga4.py não encontrado"}), 500

        result = subprocess.run(
            [sys.executable, str(script), "--days", "30"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(script.parent.parent),
        )
        out = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        data = _load_json("analytics_source.json", {})
        if data.get("success"):
            return jsonify({"success": True, "stats": data, "console": out[-1200:]})
        return jsonify({
            "success": False,
            "error": out[-1200:],
            "detail": "Script rodou mas não gerou dados. Verifique a credencial do Site Kit.",
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@traffic_bp.route("/ga4/timeseries")
@login_required
def api_traffic_ga4_timeseries():
    """Return cached GA4 time series (daily sessions)."""
    return jsonify(_load_json("analytics_timeseries.json", {
        "success": False,
        "error": "sem dados de série temporal ainda",
    }))


@traffic_bp.route("/ga4/timeseries/refresh", methods=["POST"])
@login_required
def api_traffic_ga4_timeseries_refresh():
    """Execute scripts/analytics_ga4.py --timeseries to pull live GA4 time series into cache."""
    try:
        script = _scripts_dir() / "analytics_ga4.py"
        if not script.exists():
            return jsonify({"success": False, "error": "script analytics_ga4.py não encontrado"}), 500

        result = subprocess.run(
            [sys.executable, str(script), "--days", "30", "--timeseries"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(script.parent.parent),
        )
        out = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        data = _load_json("analytics_timeseries.json", {})
        if data.get("success"):
            return jsonify({"success": True, "stats": data, "console": out[-1200:]})
        return jsonify({
            "success": False,
            "error": out[-1200:],
            "detail": "Script rodou mas não gerou dados de série temporal. Verifique a credencial do Site Kit.",
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@traffic_bp.route("/pinterest")
@login_required
def api_traffic_pinterest():
    """Extract Pinterest referral traffic from GA4 cache."""
    data = _load_json("analytics_source.json", {})
    if not data.get("success"):
        return jsonify({"success": False, "error": "GA4 ainda sem dados."})
    pinterest = next((s for s in data.get("sources", [])
                      if "pinterest" in s.get("source", "").lower()), None)
    return jsonify({
        "success": True,
        "pinterest": pinterest,
        "all_sources": data.get("sources", []),
        "fetched_at": data.get("fetched_at"),
        "total_sessions": sum(s.get("sessions", 0) for s in data.get("sources", [])),
    })


@traffic_bp.route("/bing")
@login_required
def api_traffic_bing():
    """Return cached Bing impressions/clicks."""
    return jsonify(_load_json("bing_stats.json", {
        "success": False,
        "error": "sem dados ainda",
    }))


@traffic_bp.route("/bing/refresh", methods=["POST"])
@login_required
def api_traffic_bing_refresh():
    """Execute scripts/analytics_bing.py to pull live Bing metrics into cache."""
    try:
        script = _scripts_dir() / "analytics_bing.py"
        if not script.exists():
            return jsonify({"success": False, "error": "script analytics_bing.py não encontrado"}), 500

        result = subprocess.run(
            [sys.executable, str(script), "--days", "30"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(script.parent.parent),
        )
        out = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        data = _load_json("bing_stats.json", {})
        if data.get("success"):
            return jsonify({"success": True, "stats": data, "console": out[-1200:]})
        return jsonify({
            "success": False,
            "error": out[-1200:],
            "detail": "Script rodou mas não gerou dados. Verifique BING_API_KEY no .env.",
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500