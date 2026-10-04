#!/usr/bin/env python3
"""Copia o essencial de htdocs/wp-content → addon/wp-content via FTP.

Estratégia: arquivos um a um (poucos — plugins são pequenos), pastas
recurssivas com mkd silencioso. Mostra progresso por item.
"""
import io
import os
import sys
import time
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=60)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

ORIGEM = "htdocs"
DESTINO = "techtips.dpdns.org/htdocs"

copiados = {"arq": 0, "bytes": 0, "falhas": []}


def copia_arquivo(src: str, dst: str) -> bool:
    # retomável: se já existe no destino com o mesmo tamanho, pula
    try:
        tam_orig = ftp.size(src)
    except ftplib.error_perm:
        tam_orig = None
    try:
        tam_dst = ftp.size(dst)
        if tam_orig is not None and tam_dst == tam_orig:
            return True  # já copiado em execução anterior
    except ftplib.error_perm:
        pass
    for tentativa in range(3):  # retry: FTP instável, timeout não mata mais
        try:
            buf = []
            ftp.retrbinary(f"RETR {src}", buf.append)
            dados = b"".join(buf)
            ftp.storbinary(f"STOR {dst}", io.BytesIO(dados))
            copiados["arq"] += 1
            copiados["bytes"] += len(dados)
            return True
        except (ftplib.error_perm, TimeoutError, OSError) as e:
            if tentativa == 2:
                copiados["falhas"].append((src, f"{type(e).__name__}: {e}"))
                return False
            time.sleep(3)
            try:  # reconecta se a sessão caiu
                ftp.voidcmd("NOOP")
            except Exception:  # noqa: BLE001
                ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))
    return False


def garante_dir(remoto: str):
    partes = remoto.split("/")
    caminho = ""
    for p in partes:
        caminho = f"{caminho}/{p}" if caminho else p
        try:
            ftp.mkd(caminho)
        except ftplib.error_perm:
            pass  # já existe


def copia_pasta(src: str, dst: str, nivel: int = 0):
    if nivel > 4:
        return
    try:
        entradas = ftp.nlst(src)
    except ftplib.error_perm:
        return
    for e in entradas:
        nome = e.rstrip("/").split("/")[-1]
        if nome in (".", ".."):
            continue
        alvo = f"{dst}/{nome}"
        try:
            ftp.size(e)  # arquivo?
            copia_arquivo(e, alvo)
        except ftplib.error_perm:  # pasta
            garante_dir(alvo)
            copia_pasta(e, alvo, nivel + 1)


# ── 1. TEMA Astra (o que o banco espera) ──────────────────────────────────
print("── tema astra ──")
t0 = time.time()
garante_dir(f"{DESTINO}/wp-content/themes")
copia_pasta(f"{ORIGEM}/wp-content/themes/astra", f"{DESTINO}/wp-content/themes/astra")
print(f"   {copiados['arq']} arquivos em {time.time()-t0:.0f}s")

# ── 2. Plugins (menos hello.php que é lixo) ───────────────────────────────
print("── plugins ──")
for plugin in ("akismet", "loginizer", "loginizer-security", "w3-total-cache",
               "astra-sites", "wordpress-seo", "wp-super-cache", "contact-form-7"):
    antes = copiados["arq"]
    try:
        ftp.size(f"{ORIGEM}/wp-content/plugins/{plugin}")
        copia_arquivo(f"{ORIGEM}/wp-content/plugins/{plugin}",
                      f"{DESTINO}/wp-content/plugins/{plugin}")
    except ftplib.error_perm:
        garante_dir(f"{DESTINO}/wp-content/plugins/{plugin}")
        copia_pasta(f"{ORIGEM}/wp-content/plugins/{plugin}",
                    f"{DESTINO}/wp-content/plugins/{plugin}")
    print(f"   {plugin}: +{copiados['arq']-antes}")

# ── 3. mu-plugin GA4/SEO (canonical/meta/sitemap) ─────────────────────────
print("── mu-plugins ──")
garante_dir(f"{DESTINO}/wp-content/mu-plugins")
antes = copiados["arq"]
copia_arquivo(f"{ORIGEM}/wp-content/mu-plugins/tech-tips-ga4-seo.php",
              f"{DESTINO}/wp-content/mu-plugins/tech-tips-ga4-seo.php")
print(f"   tech-tips-ga4-seo.php: +{copiados['arq']-antes}")

# ── 4. uploads (se existir) ───────────────────────────────────────────────
print("── uploads ──")
try:
    entradas = ftp.nlst(f"{ORIGEM}/wp-content/uploads")
    reais = [e for e in entradas if e.rstrip("/").split("/")[-1] not in (".", "..")]
    if reais:
        copia_pasta(f"{ORIGEM}/wp-content/uploads", f"{DESTINO}/wp-content/uploads")
    else:
        print("   (vazio — nada a copiar)")
except ftplib.error_perm:
    print("   (não existe)")

ftp.quit()
pulados = copiados.get("pulados", 0)
print(f"\n✅ {copiados['arq']} arquivos copiados, {pulados} pulados (já existiam), "
      f"{copiados['bytes']/1024:.0f} KB transferidos")
if copiados["falhas"]:
    print(f"⚠️ {len(copiados['falhas'])} falhas:")
    for f, e in copiados["falhas"][:10]:
        print(f"   {f}: {e}")
