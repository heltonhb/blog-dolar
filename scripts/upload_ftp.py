#!/usr/bin/env python3
"""Upload artigo via FTP e criar script PHP para publicar no WordPress"""

import ftplib
import os
from pathlib import Path

# Config FTP — lidas do ambiente (nunca hardcode!)
ftp_host = os.environ.get('FTP_HOST', 'ftpupload.net')
ftp_user = os.environ.get('FTP_USER', '')
ftp_pass = os.environ.get('FTP_PASS', '')

if not ftp_user or not ftp_pass:
    print("ERRO: configure FTP_USER e FTP_PASS no arquivo .env")
    raise SystemExit(1)

# Ler o artigo
article_path = Path('articles/2026-08-31_how-to-protect-your-digital-privacy-online.md')
content = article_path.read_text(encoding='utf-8')

# Extrair frontmatter
article = {'content': content}
if content.startswith('---'):
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[1]
        article['content'] = parts[2].strip()
        for line in frontmatter.strip().split('\n'):
            if ':' in line:
                key, _, val = line.partition(':')
                val = val.strip().strip('"[]')
                article[key.strip()] = val.split(',')[0]

print(f'Titulo: {article.get("title", "N/A")}')
print(f'Slug: {article.get("slug", "N/A")}')

# Criar script PHP
title = article.get('title', 'Untitled')
post_content = article.get('content', '')
slug = article.get('slug', '')
excerpt = article.get('meta_description', '')
tags = article.get('tags', '')

php_script = f"""<?php
// Publicar artigo via API do WordPress (executar no servidor)
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {{
    require_once($wp_load);
}} else {{
    echo 'wp-load.php not found';
    exit;
}}

// Dados do artigo
$post_data = array(
    'post_title' => '{title}',
    'post_content' => '{post_content.replace("'", "\\'")}',
    'post_name' => '{slug}',
    'post_excerpt' => '{excerpt.replace("'", "\\'")}',
    'post_status' => 'draft',
    'post_author' => 1
);

// Inserir post
$post_id = wp_insert_post($post_data);

if ($post_id) {{
    echo 'Post criado com sucesso! ID: ' . $post_id . PHP_EOL;
    echo 'Link: ' . get_permalink($post_id) . PHP_EOL;

    // Adicionar tags se existirem
    $tags = '{tags}';
    if ($tags) {{
        wp_set_post_tags($post_id, $tags);
    }}
}} else {{
    echo 'Erro ao criar post' . PHP_EOL;
}}
?>"""

# Upload via FTP
ftp = ftplib.FTP(ftp_host, timeout=15)
ftp.login(ftp_user, ftp_pass)
ftp.cwd('htdocs')

# Salvar temporariamente
temp_path = Path('/tmp/wp_publish.php')
temp_path.write_text(php_script)

# Upload
with open(temp_path, 'rb') as f:
    ftp.storbinary('STOR wp_publish.php', f)

print('\nScript PHP uploadado!')
print('Para publicar, acesse: http://tech-tips.ct.ws/wp_publish.php')
print('OU publique manualmente pelo wp-admin quando o site voltar')

ftp.quit()
