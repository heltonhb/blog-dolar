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
    """Solve ByetHost/InfinityFree AES challenge. Uses Node.js slowAES."""
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return None
    a, b, c = matches[0], matches[1], matches[2]

    import httpx as _httpx
    import subprocess as _sp
    import tempfile as _tmp

    # Fetch aes.js from the site
    if not site_url:
        site_url = _env("SITE_URL", "https://tech-tips.ct.ws")
    try:
        aes_resp = _httpx.get(f"{site_url.rstrip('/')}/aes.js", timeout=10, verify=False)
        aes_js = aes_resp.text
    except Exception:
        return None

    # Node.js script using the real slowAES
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
        return cookie if cookie else None
    except Exception:
        return None
    finally:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except Exception:
                pass


def _antibot_session(site_url: str = ""):
    """Create an httpx Client with the anti-bot cookie resolved."""
    import httpx as _httpx
    from urllib.parse import urlparse

    if not site_url:
        env = _load_env_dict()
        site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.ct.ws")

    domain = urlparse(site_url).hostname
    client = _httpx.Client(timeout=30, verify=False, follow_redirects=True)
    try:
        resp = client.get(f"{site_url.rstrip('/')}/", timeout=15)
        html = resp.text
        if "toNumbers" in html and "slowAES" in html:
            cookie_val = _solve_challenge(html, site_url)
            if cookie_val:
                client.cookies.set("__test", cookie_val, domain=domain)
                # Verify the cookie works
                try:
                    test = client.get(f"{site_url.rstrip('/')}/wp-json/", timeout=10)
                    if test.status_code == 200 and "name" in test.text[:200]:
                        return client
                except Exception:
                    pass
                # Retry with extra request
                try:
                    client.get(f"{site_url.rstrip('/')}/?i=1", timeout=10)
                except Exception:
                    pass
                raise RuntimeError(
                    f"Falha ao resolver anti-bot de {domain}: cookie inválido. Tente novamente."
                )
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Falha ao conectar com {domain}: {e}")
    return client


# Keep backward-compatible alias
_byethost_session = _antibot_session


# ---------------------------------------------------------------------------
#  WordPress REST API
# ---------------------------------------------------------------------------

def _wp_publish(article: dict, status: str = "publish") -> dict:
    """Publish via WordPress REST API. Returns {success, id, link, error}."""
    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.ct.ws")
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
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.ct.ws")
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
