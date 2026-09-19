# -*- coding: utf-8 -*-
"""AdCash and Adsterra monetization API routes."""
from datetime import datetime

import httpx
from flask import Blueprint, jsonify

from dashboard.services.helpers import _env, login_required
from db import get_config, save_config

monetization_bp = Blueprint("monetization", __name__, url_prefix="/api")


@monetization_bp.route("/adcash")
@login_required
def api_adcash():
    """Return cached AdCash publisher statistics."""
    return jsonify(get_config("adcash_stats", {}))


@monetization_bp.route("/adcash/refresh", methods=["POST"])
@login_required
def api_adcash_refresh():
    """Fetch live report stats from AdCash Publisher API."""
    try:
        config = get_config("adcash_config", {})
        token = _env("ADCASH_API_TOKEN") or config.get("api_token", "")
        zone_id = _env("ADCASH_ZONE_ID") or config.get("zone_id", "")

        if not token:
            return jsonify({
                "success": False,
                "error": "Token AdCash não configurado. Adicione ADCASH_API_TOKEN em Config.",
            }), 400

        stats = get_config("adcash_stats", {})
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m-01")

        try:
            resp = httpx.get(
                "https://adcash.myadcash.com/api/v2/publishers/reports",
                params={
                    "start_date": month_start,
                    "end_date": today,
                    "group_by": "date",
                    "filters[zone]": zone_id,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                api_data = resp.json()
                rows = api_data.get("data", {}).get("rows", [])

                total_revenue = sum(float(r.get("revenue", r.get("earnings", 0))) for r in rows)
                total_impressions = sum(int(r.get("impressions", 0)) for r in rows)
                total_clicks = sum(int(r.get("clicks", 0)) for r in rows)
                avg_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0

                daily_stats = []
                for row in rows:
                    daily_stats.append({
                        "date": row.get("date", row.get("day", "")),
                        "impressions": int(row.get("impressions", 0)),
                        "clicks": int(row.get("clicks", 0)),
                        "revenue": float(row.get("revenue", row.get("earnings", 0))),
                        "ecpm": float(row.get("ecpm", 0)),
                    })

                stats.update({
                    "total_revenue": round(total_revenue, 4),
                    "total_impressions": total_impressions,
                    "total_clicks": total_clicks,
                    "avg_ecpm": round(avg_ecpm, 2),
                    "daily_stats": daily_stats,
                    "last_updated": datetime.now().isoformat(),
                    "api_status": "ok",
                })
            else:
                stats["last_updated"] = datetime.now().isoformat()
                stats["api_status"] = f"error_{resp.status_code}"
                stats["api_error"] = resp.text[:200]
        except Exception as api_err:
            stats["last_updated"] = datetime.now().isoformat()
            stats["api_status"] = "unreachable"
            stats["api_error"] = str(api_err)

        save_config("adcash_stats", stats)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@monetization_bp.route("/adsterra")
@login_required
def api_adsterra():
    """Fetch stats from Adsterra Publisher API."""
    token = _env("ADSTERRA_API_TOKEN", "")
    if not token:
        return jsonify({
            "success": False,
            "error": "Token Adsterra não configurado. Gere em: https://beta.publishers.adsterra.com → API",
        }), 400

    today = datetime.now().strftime("%Y-%m-%d")
    month_start = datetime.now().strftime("%Y-%m-01")

    try:
        resp = httpx.get(
            "https://api3.adsterratools.com/publisher/stats.json",
            params={
                "start_date": month_start,
                "finish_date": today,
                "group_by": "date",
            },
            headers={"X-API-Key": token},
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            stats_list = data.get("items", [])

            total_revenue = sum(float(s.get("revenue", 0)) for s in stats_list)
            total_impressions = sum(int(s.get("impression", 0)) for s in stats_list)
            total_clicks = sum(int(s.get("clicks", 0)) for s in stats_list)
            avg_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0

            daily = []
            for s in stats_list:
                daily.append({
                    "date": s.get("date", ""),
                    "impressions": int(s.get("impression", 0)),
                    "clicks": int(s.get("clicks", 0)),
                    "revenue": float(s.get("revenue", 0)),
                    "ecpm": float(s.get("cpm", 0)),
                })

            result = {
                "success": True,
                "total_revenue": round(total_revenue, 4),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "avg_ecpm": round(avg_ecpm, 2),
                "daily_stats": daily,
                "last_updated": datetime.now().isoformat(),
                "api_status": "ok",
            }
            save_config("adsterra_stats", result)
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@monetization_bp.route("/adsterra/domains")
@login_required
def api_adsterra_domains():
    """Get list of registered domains from Adsterra."""
    token = _env("ADSTERRA_API_TOKEN", "")
    if not token:
        return jsonify({"success": False, "error": "Token não configurado"}), 400

    try:
        resp = httpx.get(
            "https://api3.adsterratools.com/publisher/websites",
            headers={"X-API-Key": token},
            timeout=15,
        )
        return jsonify(resp.json() if resp.status_code == 200 else {"error": resp.text[:200]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
