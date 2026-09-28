# -*- coding: utf-8 -*-
"""WordPress REST API and anti-bot challenge solver."""
import ftplib
import os
import re
from pathlib import Path

from .helpers import _env, _load_env_dict


# ---------------------------------------------------------------------------
#  Anti-bot challenge solver (ByetHost / InfinityFree)
# ---------------------------------------------------------------------------

def _solve_challenge(html: str, site_url: str = ""):
    """Solve ByetHost/InfinityFree AES challenge.

    Tries Node.js (running the site's own slowAES) first, then falls back to
    pure-Python AES-CBC via pycryptodome — works even where Node.js is absent
    (e.g. some PaaS images). slowAES uses lenient PKCS7, so padding is only
    stripped when the length byte is in range.
    """
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return None
    a, b, c = matches[0], matches[1], matches[2]

    if not site_url:
        site_url = _env("SITE_URL", "https://techtips.dpdns.org")

    # --- Attempt 1: Node.js with the site's own slowAES ---
    try:
        import httpx as _httpx
        import subprocess as _sp
        import tempfile as _tmp

        aes_resp = _httpx.get(f"{site_url.rstrip('/')}/aes.js", timeout=10, verify=False)
        aes_js = aes_resp.text
        if "slowAES" in aes_js:  # /aes.js may itself be swapped by the challenge page
            node_code = (
                aes_js + "\n"
                'function toNumbers(d){var e=[];d.replace(/(..)/g,function(d){e.push(parseInt(d,16))});return e}\n'
                'function toHex(){for(var d=[],d=1==arguments.length&&arguments[0].constructor==Array?arguments[0]:arguments,e="",f=0;f<d.length;f++)e+=(16>d[f]?"0":"")+d[f].toString(16);return e.toLowerCase()}\n'
                f'var a=toNumbers("{a}"),b=toNumbers("{b}"),c=toNumbers("{c}");\n'
                'console.log(toHex(slowAES.decrypt(c,2,a,b)));\n'
            )
            tmpfile = None
            try:
                with _tmp.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
                    f.write(node_code)
                    tmpfile = f.name
                result = _sp.run(["node", tmpfile], capture_output=True, text=True, timeout=10)
                cookie = result.stdout.strip()
                if cookie:
                    return cookie
            finally:
                if tmpfile:
                    try:
                        os.unlink(tmpfile)
                    except Exception:
                        pass
    except Exception:
        pass  # Node missing/failed → fall through to pure-Python solver

    # --- Attempt 2: pure-Python AES-CBC (pycryptodome) ---
    try:
        from Crypto.Cipher import AES

        cipher = AES.new(bytes.fromhex(a), AES.MODE_CBC, bytes.fromhex(b))
        decrypted = cipher.decrypt(bytes.fromhex(c))
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            decrypted = decrypted[:-pad_len]
        return decrypted.hex()
    except Exception:
        return None


# Cache of solved cookies: domain -> (cookie_value, timestamp)
_ANTIBOT_COOKIE_CACHE: dict = {}


def _antibot_session(site_url: str = ""):
    """Create an httpx Client with the anti-bot cookie resolved.

    The solved cookie is cached per domain (server-side valid 6h, reused for
    5h) so repeated calls in one process don't re-solve the challenge and trip
    InfinityFree rate limiting. Verification is retried before giving up.
    """
    import time as _time
    import httpx as _httpx
    from urllib.parse import urlparse

    if not site_url:
        env = _load_env_dict()
        site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
    base = site_url.rstrip("/")
    domain = urlparse(site_url).hostname or ""

    def _client_with(cookie_val: str = ""):
        c = _httpx.Client(timeout=30, verify=False, follow_redirects=True)
        if cookie_val:
            c.cookies.set("__test", cookie_val, domain=domain)
        return c

    def _verified(client) -> bool:
        try:
            test = client.get(f"{base}/wp-json/", timeout=15)
            return test.status_code == 200 and "name" in test.text[:200]
        except Exception:
            return False

    # 1) Reuse cached cookie
    cached = _ANTIBOT_COOKIE_CACHE.get(domain)
    if cached and _time.time() - cached[1] < 5 * 3600:
        client = _client_with(cached[0])
        if _verified(client):
            return client

    # 2) Fresh solve, up to 2 attempts
    last_error = ""
    for _attempt in range(2):
        client = _client_with()
        try:
            resp = client.get(f"{base}/", timeout=20)
        except Exception as e:
            raise RuntimeError(f"Falha ao conectar com {domain}: {e}")
        html = resp.text
        if "toNumbers" not in html or "slowAES" not in html:
            return client  # no challenge present
        cookie_val = _solve_challenge(html, base)
        if not cookie_val:
            last_error = "desafio não pôde ser decifrado (Node.js e pycryptodome falharam)"
            continue
        client = _client_with(cookie_val)
        if _verified(client):
            _ANTIBOT_COOKIE_CACHE[domain] = (cookie_val, _time.time())
            return client
        # one extra hop the challenge expects, then re-verify
        try:
            client.get(f"{base}/?i=1", timeout=15)
        except Exception:
            pass
        if _verified(client):
            _ANTIBOT_COOKIE_CACHE[domain] = (cookie_val, _time.time())
            return client
        last_error = f"cookie recusado ao testar {base}/wp-json/"

    raise RuntimeError(
        f"Falha ao resolver anti-bot de {domain}: {last_error or 'cookie inválido'}. Tente novamente."
    )


# Keep backward-compatible alias
_byethost_session = _antibot_session


# ---------------------------------------------------------------------------
#  WordPress REST API
# ---------------------------------------------------------------------------

def _wp_publish(article: dict, status: str = "publish") -> dict:
    """Publish via WordPress REST API. Returns {success, id, link, error}."""
    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    if not wp_user or not wp_pass:
        return {"success": False, "error": "Configure WP_USER e WP_APP_PASSWORD nas configurações"}

    base_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"
    auth = (wp_user, wp_pass)

    # Add hreflang for US targeting
    slug = article.get("slug", "")
    hreflang_tag = f'<link rel="alternate" hreflang="en-us" href="{site_url.rstrip("/")}/?p={slug}" />'
    article_content = article.get("content", "")
    if "<head>" in article_content:
        article_content = article_content.replace("<head>", f"<head>\n{hreflang_tag}")
    elif "<html>" in article_content:
        article_content = article_content.replace("<html>", f"<html>\n<head>{hreflang_tag}</head>")

    payload = {
        "title": article.get("title", "Untitled"),
        "content": article_content,
        "slug": slug,
        "excerpt": article.get("meta_description", ""),
        "status": status,
        "meta": {"_yoast_wpseo_metadesc": article.get("meta_description", "")},
    }
    if article.get("featured_media_id"):
        payload["featured_media"] = article["featured_media_id"]

    try:
        client = _antibot_session(site_url)
        resp = client.post(f"{base_url}/posts", auth=auth, json=payload)
        if resp.status_code in (200, 201):
            try:
                post = resp.json()
            except Exception:
                return {"success": False, "error": f"Resposta inválida do WordPress (HTTP {resp.status_code}): {resp.text[:300]}"}
            return {"success": True, "id": post.get("id"), "link": post.get("link", ""), "status": post.get("status")}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wp_upload_media(image_bytes: bytes, filename: str, alt_text: str = "") -> dict:
    """Upload image to WP media library. Returns {success, id, url, error}."""
    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    if not wp_user or not wp_pass:
        return {"success": False, "error": "WP_USER/WP_APP_PASSWORD não configurados"}

    base_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"
    try:
        client = _antibot_session(site_url)
        resp = client.post(
            f"{base_url}/media",
            auth=(wp_user, wp_pass),
            content=image_bytes,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "image/png",
            },
        )
        if resp.status_code in (200, 201):
            try:
                media = resp.json()
            except Exception:
                return {"success": False, "error": f"Resposta inválida do WordPress (HTTP {resp.status_code}): {resp.text[:200]}"}
            media_id = media.get("id")
            media_url = media.get("source_url", "")
            if alt_text and media_id:
                client.post(f"{base_url}/media/{media_id}", auth=(wp_user, wp_pass),
                            json={"alt_text": alt_text})
            return {"success": True, "id": media_id, "url": media_url}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  FTP cleanup (legacy)
# ---------------------------------------------------------------------------

def _cleanup_ftp(host, user, password):
    """Remove temporary auto-publish script files via FTP."""
    try:
        ftp = ftplib.FTP(host, timeout=15)
        ftp.login(user, password)
        ftp.cwd("htdocs")
        for f in ("auto-publish.php", "article_body.html"):
            try:
                ftp.delete(f)
            except Exception:
                pass
        ftp.quit()
    except Exception:
        pass
