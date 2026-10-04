#!/usr/bin/env python3
"""Migração Plano G — etapa 4: migrar URLs no banco (search-replace).

MySQL da InfinityFree não aceita conexão externa, então o search-replace
roda como PHP no próprio addon: carrega o WP uma vez (wp-load.php) e usa
$wpdb->query com UPDATEs diretos.

O que faz:
  1. wptl_options: siteurl e home → https://techtips.dpdns.org
     (redundante com WP_HOME/WP_SITEURL no wp-config, mas deixa o banco correto)
  2. wptl_posts: search-replace tech-tips.ct.ws → techtips.dpdns.org
     (post_content com links internos, guid, etc.)
  3. Relata contagens ANTES/DEPOIS de cada tabela.

Segurança: o script se auto-remove após executar (unlink __FILE__).
"""
import io
import os
import re
import sys
import urllib.request
from pathlib import Path

import ftplib
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

NOVO = "https://techtips.dpdns.org"
PHP = f"""<?php
header('Content-Type: text/plain');
define('WP_USE_THEMES', false);
require_once __DIR__ . '/wp-load.php';
global $wpdb;
$prefix = $wpdb->prefix;
$antigo = 'https://tech-tips.ct.ws';
$novo = '{NOVO}';

echo "== ANTES ==\\n";
foreach (array('siteurl', 'home') as $opt) {{
    echo "$opt: " . get_option($opt) . "\\n";
}}
$cont_ctws = $wpdb->get_var("SELECT COUNT(*) FROM {{$wpdb->posts}} WHERE post_content LIKE '%tech-tips.ct.ws%' OR guid LIKE '%tech-tips.ct.ws%'");
$cont_guid = $wpdb->get_var("SELECT COUNT(*) FROM {{$wpdb->posts}} WHERE guid LIKE '%tech-tips.ct.ws%'");
echo "posts com ct.ws (content+guid): $cont_ctws\\n";

// 1. siteurl/home
$wpdb->query($wpdb->prepare(
    "UPDATE {{$wpdb->options}} SET option_value = %s WHERE option_name IN ('siteurl', 'home')",
    $novo
));
echo "== siteurl/home atualizados ==\\n";

// 2. search-replace nos posts (content + guid)
$wpdb->query("UPDATE {{$wpdb->posts}} SET post_content = REPLACE(post_content, '$antigo', '$novo')");
$wpdb->query("UPDATE {{$wpdb->posts}} SET guid = REPLACE(guid, '$antigo', '$novo')");
echo "== search-replace em posts feito ==\\n";

// 3. postmeta (links internos em meta, se houver)
$wpdb->query("UPDATE {{$wpdb->postmeta}} SET meta_value = REPLACE(meta_value, '$antigo', '$novo') WHERE meta_value LIKE '%tech-tips.ct.ws%'");
echo "== postmeta varrido ==\\n";

// 4. options (pode ter URLs absolutas em widgets/tema)
$wpdb->query("UPDATE {{$wpdb->options}} SET option_value = REPLACE(option_value, '$antigo', '$novo') WHERE option_value LIKE '%tech-tips.ct.ws%'");
echo "== options varridas ==\\n";

echo "== DEPOIS ==\\n";
foreach (array('siteurl', 'home') as $opt) {{
    echo "$opt: " . get_option($opt) . "\\n";
}}
$resto = $wpdb->get_var("SELECT COUNT(*) FROM {{$wpdb->posts}} WHERE post_content LIKE '%tech-tips.ct.ws%' OR guid LIKE '%tech-tips.ct.ws%'");
echo "posts ainda com ct.ws: $resto\\n";
echo "FIM\\n";
@unlink(__FILE__);
"""

ftp.storbinary(
    "STOR techtips.dpdns.org/htdocs/_migra_urls.php",
    io.BytesIO(PHP.encode()),
)
ftp.quit()
print("✅ _migra_urls.php enviado")

# executa atravessando o anti-bot
antibot.SITE = "https://techtips.dpdns.org"
url = f"{antibot.SITE}/_migra_urls.php"
html = antibot.get_pagina(url)
print(html)