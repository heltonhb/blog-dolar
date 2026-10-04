#!/usr/bin/env python3
"""Expande o post thin (top-essential-tech-tips-2026) para ~900 palavras.

Escreve conteúdo novo no padrão do site (h2/h3, parágrafos, listas),
atualiza via REST WP (PUT com anti-bot) e o excerpt (o mu-plugin lê
a meta description dele).
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE, get, solve_challenge  # noqa: E402
from fetch_wp_post import _rest_get, _auth_header  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

SLUG = "top-essential-tech-tips-2026"

NOVO_CONTEUDO = """
<h2>Why Tech Habits Matter More Than Ever in 2026</h2>
<p>Technology moves fast, but the habits that keep you safe, productive, and ahead of the curve are surprisingly stable. In 2026, with AI tools embedded in almost every app and cyber threats growing more sophisticated, the essentials are no longer optional. Whether you are a student, a professional, or just someone who wants to stop fighting their devices, these are the tech tips that actually matter this year.</p>
<p>We have cut through the noise to bring you only the advice that delivers real results. No gimmicks, no expensive gadgets — just practical changes you can make today.</p>

<h2>1. Use a Password Manager (and Stop Reusing Passwords)</h2>
<p>Still juggling a handful of passwords across dozens of accounts? This is the single biggest security risk most people carry. A password manager generates and stores unique, complex passwords for every service you use, and you only need to remember one master password.</p>
<p>Popular options like Bitwarden (free and open source), 1Password, and Proton Pass work across all your devices. Setup takes about 20 minutes, and the payoff is immediate: one leaked database no longer puts your entire digital life at risk.</p>

<h2>2. Turn On Two-Factor Authentication Everywhere</h2>
<p>Passwords alone are not enough anymore. Two-factor authentication (2FA) adds a second lock to your accounts, usually a code from your phone or an authenticator app. Focus on the accounts that matter most: email, banking, cloud storage, and social media.</p>
<p>Prefer authenticator apps (Google Authenticator, Authy, or 2FAS) over SMS codes when possible — SIM swapping attacks make text messages the weakest link. It takes two minutes per account and blocks the vast majority of automated attacks.</p>

<h2>3. Automate Your Backups Before You Need Them</h2>
<p>Everyone knows they should back up their files — until the day a drive fails or ransomware locks everything. The 3-2-1 rule still holds: keep three copies of important data, on two different types of media, with one copy off-site.</p>
<p>Cloud storage like Google Drive, OneDrive, or Backblaze makes this nearly effortless. Set it once, verify it monthly by actually restoring a file, and stop thinking about it. A backup you have never tested is a hope, not a plan.</p>

<h2>4. Master Keyboard Shortcuts for Your Daily Tools</h2>
<p>The average computer user wastes hours every month reaching for the mouse. Learning just ten shortcuts for your browser, text editor, and file manager compounds into serious time savings over a year.</p>
<p>Start with the universal ones: <code>Ctrl+C</code>/<code>Ctrl+V</code> for copy and paste, <code>Alt+Tab</code> to switch windows, <code>Ctrl+F</code> to find text on a page, and <code>Win+V</code> (Windows) or clipboard history to paste earlier items. Then add app-specific shortcuts for whatever you use most — your future self will thank you.</p>

<h2>5. Keep Your Software Updated — Yes, Even When It's Inconvenient</h2>
<p>Most successful attacks exploit vulnerabilities that were already patched months earlier. Updates are not just about new features; they are the maintenance that keeps the doors locked.</p>
<p>Turn on automatic updates for your operating system, browser, and phone. For everything else, do a quick monthly review. If you run a WordPress site or any self-hosted software, treat updates as urgent, not optional.</p>

<h2>6. Clean Your Digital Clutter Quarterly</h2>
<p>Digital hoarding slows down devices, exposes old data, and makes finding anything harder. Once a quarter, spend an hour on maintenance: delete apps you have not opened in months, clear your downloads folder, review browser extensions, and audit the permissions you have granted to apps and websites.</p>
<p>Extensions deserve special attention — outdated or shady browser extensions can read everything you do online. If you do not recognize it or use it, remove it.</p>

<h2>7. Learn One AI Tool Properly Instead of Ten Superficially</h2>
<p>AI assistants are everywhere in 2026, but the value comes from depth, not breadth. Pick the tool that fits your workflow — an AI writing assistant for documents, a coding copilot for development, or a research assistant for studying — and learn it properly.</p>
<p>Learn to write clear prompts with context and examples, save the prompts that work, and integrate the tool into a real task you repeat weekly. One well-learned tool saves more time than a dozen you open once and forget.</p>

<h2>8. Secure Your Home Wi-Fi in 10 Minutes</h2>
<p>Your Wi-Fi router is the front door to every device in your home. Change the default admin password, use WPA3 (or at least WPA2) encryption with a strong passphrase, and disable remote administration unless you truly need it.</p>
<p>While you are at it, check for router firmware updates — many ISP-provided routers never get updated unless you do it manually. For more depth, our guide on <a href="https://techtips.dpdns.org/2026/09/01/how-to-fix-slow-wifi-troubleshooting-guide/">fixing slow Wi-Fi</a> walks through the full troubleshooting process.</p>

<h2>9. Declutter Your Inbox with Filters and Unsubscribe Ruthlessly</h2>
<p>An inbox with 10,000 unread emails is not a productivity system. Dedicate one session to unsubscribing from newsletters you never read, then set up filters so the remaining messages sort themselves into folders automatically.</p>
<p>Gmail, Outlook, and Proton Mail all support rules that can archive, label, or delete mail before it ever hits your main inbox. Ten minutes of setup saves hundreds of interruptions later.</p>

<h2>10. Know What Google Knows About You</h2>
<p>Your Google account holds your search history, location data, voice recordings, and more. The <strong>Google Takeout</strong> and <strong>My Activity</strong> pages let you see, download, and delete this data on a schedule. You can also set history to auto-delete after 3, 18, or 36 months.</p>
<p>Reducing your digital footprint does not require going off the grid — just knowing where the levers are and pulling the ones that matter to you. For a deeper dive, see our guide on <a href="https://techtips.dpdns.org/2026/08/31/how-to-protect-your-digital-privacy-online/">protecting your digital privacy online</a>.</p>

<h2>Small Habits, Big Results</h2>
<p>You do not need to implement all ten tips this weekend. Pick two — ideally the password manager and 2FA — and build from there. Each one takes minutes to set up and pays off quietly for years. That is the real secret of tech-savvy people: not expensive gadgets, but boring habits executed consistently.</p>
<p>Want to go further? Explore our other guides on <a href="https://techtips.dpdns.org/">Tech Tips</a> — from hardware buying advice to learning the tools that power modern development.</p>
"""

NOVO_EXCERPT = (
    "The essential tech tips for 2026: password managers, 2FA, automated backups, "
    "keyboard shortcuts, AI tools, and more — practical habits that keep you safe "
    "and productive."
)


def _put_post(post_id: int, payload: dict) -> bool:
    url = f"{SITE}/wp-json/wp/v2/posts/{post_id}"
    cookie = solve_challenge(get(f"{SITE}/wp-sitemap.xml"))

    def _put(extra):
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        headers.update(_auth_header())
        headers.update(extra)
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=headers, method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:200]}") from e

    corpo = _put({"Cookie": f"__test={cookie}"})
    if "toNumbers" in corpo:
        cookie = solve_challenge(get(f"{SITE}/wp-sitemap.xml"))
        corpo = _put({"Cookie": f"__test={cookie}"})
    return corpo.strip().startswith("{")


def main():
    # id do post
    raw = _rest_get(f"{SITE}/wp-json/wp/v2/posts?slug={SLUG}&_fields=id,slug,content")
    posts = json.loads(raw)
    if not posts:
        sys.exit(f"post {SLUG} não encontrado")
    pid = posts[0]["id"]
    palavras_atuais = len(re.sub(r"<[^>]+>", " ", posts[0]["content"]["rendered"]).split())
    print(f"post id={pid} | palavras antes: {palavras_atuais}")

    payload = {"content": NOVO_CONTEUDO, "excerpt": NOVO_EXCERPT}
    if _put_post(pid, payload):
        palavras_novas = len(re.sub(r"<[^>]+>", " ", NOVO_CONTEUDO).split())
        print(f"✅ atualizado | palavras depois: ~{palavras_novas}")
    else:
        sys.exit("❌ anti-bot bloqueou o PUT")


if __name__ == "__main__":
    main()
