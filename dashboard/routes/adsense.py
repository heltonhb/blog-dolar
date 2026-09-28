# -*- coding: utf-8 -*-
"""AdSense information API: publisher id + live site status checks."""
import re
from datetime import datetime

import httpx
from flask import Blueprint, jsonify

from dashboard.services.helpers import _env, _project_root, login_required
from dashboard.services import wordpress as wp

adsense_bp = Blueprint("adsense", __name__, url_prefix="/api")

DEFAULT_PUB_ID = "ca-pub-6258036451330976"
MU_PLUGIN = "tech-tips-ga4-seo.php"


def _publisher_id() -> str:
    """Resolve the AdSense publisher id: env → mu-plugin source → default."""
    env_id = _env("ADSENSE_PUB_ID", "").strip()
    if re.fullmatch(r"ca-pub-\d+", env_id):
        return env_id
    match = re.search(r"ca-pub-\d+", _mu_plugin_source())
    return match.group(0) if match else DEFAULT_PUB_ID


def _mu_plugin_source() -> str:
    """Raw text of the mu-plugin that injects the AdSense tag (empty if missing)."""
    try:
        return (_project_root() / "scripts" / MU_PLUGIN).read_text(encoding="utf-8")
    except Exception:
        return ""


def _site_url() -> str:
    return _env("SITE_URL", "https://techtips.dpdns.org").rstrip("/")


def _fetch(path: str):
    """GET a path on the site, solving the host anti-bot challenge when possible.

    Returns (status_code | None, body, note). Never raises.
    """
    site = _site_url()
    url = f"{site}{path}"
    try:
        client = wp._antibot_session(site)
        resp = client.get(url, timeout=20)
        return resp.status_code, resp.text, ""
    except Exception as err:
        try:
            resp = httpx.get(url, timeout=20, verify=False, follow_redirects=True)
            return resp.status_code, resp.text, f"anti-bot não resolvido ({err})"
        except Exception as err2:
            return None, "", str(err2)


@adsense_bp.route("/adsense/status")
@login_required
def adsense_status():
    """Live verification that the AdSense tag/ads.txt are in place on the site."""
    pub_id = _publisher_id()
    site = _site_url()
    checks = []
    notes = []

    # --- Home page ---
    code, html, note = _fetch("/")
    if note:
        notes.append(note)
    reachable = code == 200
    checks.append({
        "key": "site",
        "label": "Site acessível (HTTPS)",
        "ok": reachable,
        "detail": f"HTTP {code} em {site}" if code else f"sem resposta: {note or 'desconhecido'}",
    })

    challenge = "toNumbers" in html and "slowAES" in html
    if challenge:
        notes.append("HTML da home protegido por anti-bot: script/meta não puderam ser lidos do servidor")

    has_script = "adsbygoogle" in html and (pub_id in html or "googlesyndication" in html)
    checks.append({
        "key": "home_script",
        "label": "Script adsbygoogle na home",
        "ok": has_script,
        "detail": (f"{pub_id} detectado no HTML" if has_script
                   else "anti-bot: não verificado" if challenge
                   else "tag não encontrada no HTML da home"),
    })

    has_meta = "google-adsense-account" in html and pub_id in html
    checks.append({
        "key": "home_meta",
        "label": "Meta google-adsense-account na home",
        "ok": has_meta,
        "detail": (f"{pub_id} detectado no HTML" if has_meta
                   else "anti-bot: não verificado" if challenge
                   else "meta não encontrada no HTML da home"),
    })

    # --- mu-plugin source (what will be/is injected in wp_head) ---
    src = _mu_plugin_source()
    mu_ok = bool(src) and pub_id in src and "adsbygoogle.js" in src and "google-adsense-account" in src
    checks.append({
        "key": "mu_plugin",
        "label": "mu-plugin local com a tag AdSense",
        "ok": mu_ok,
        "detail": (f"{MU_PLUGIN} contém script + meta" if mu_ok
                   else f"{MU_PLUGIN} não encontrado ou sem a tag" if src
                   else "arquivo do mu-plugin ausente"),
    })

    # --- ads.txt (format uses pub-XXXX, not ca-pub-XXXX) ---
    ads_code, ads_body, ads_note = _fetch("/ads.txt")
    if ads_note:
        notes.append(ads_note)
    expected = f"google.com, {re.sub(r'^ca-', '', pub_id)}"
    ads_ok = ads_code == 200 and expected in ads_body
    checks.append({
        "key": "ads_txt",
        "label": "ads.txt autorizando o Google",
        "ok": ads_ok,
        "detail": (f"linha encontrada: {expected}" if ads_ok
                   else f"HTTP {ads_code}: linha '{expected}' ausente" if ads_code
                   else f"sem resposta: {ads_note or 'desconhecido'}"),
    })

    return jsonify({
        "success": True,
        "publisher_id": pub_id,
        "site_url": site,
        "checks": checks,
        "notes": notes,
        "all_ok": all(c["ok"] for c in checks),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })
