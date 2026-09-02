#!/usr/bin/env python3
"""
Publicar artigo no WordPress - Using Node.js to solve anti-bot challenge
Usage: python3 publish_auto.py <filename>
"""

import sys
import json
import re
import subprocess
from ftplib import FTP
from io import BytesIO
from pathlib import Path
import httpx

# Config
FTP_HOST = "ftpupload.net"
FTP_USER = "b4_42799195"
FTP_PASS = "Picard170!"
DB_HOST = "sql310.byetcluster.com"
DB_USER = "42799195_1"
DB_PASS = "p6S(09[v77"
DB_NAME = "b442799195_wp909"
DB_PREFIX = "wpq9_"
SITE_URL = "https://tech-tips.byethost4.com"

def parse_frontmatter(content):
    """Parse frontmatter without YAML (handles colons in titles)"""
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    frontmatter_text = parts[1].strip()
    body = parts[2].strip()
    
    frontmatter = {}
    current_key = None
    current_value = []
    
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if ':' in line and not line.startswith(' '):
            if current_key:
                frontmatter[current_key] = ' '.join(current_value)
            key, _, value = line.partition(':')
            current_key = key.strip()
            current_value = [value.strip()] if value.strip() else []
        elif current_key:
            current_value.append(line)
    
    if current_key:
        frontmatter[current_key] = ' '.join(current_value)
    
    return frontmatter, body

def solve_challenge_with_node(html):
    """Solve the anti-bot challenge using Node.js"""
    # Extract the challenge code
    # Find: var a=toNumbers("..."), b=toNumbers("..."), c=toNumbers("...");
    # and: document.cookie="__test="+toHex(slowAES.decrypt(c,2,a,b))+...
    
    # Extract the three hex values
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return None
    
    a, b, c = matches[0], matches[1], matches[2]
    
    # Create a minimal Node.js script to solve the challenge
    node_script = f'''
const crypto = require('crypto');

// slowAES implementation (simplified)
function toNumbers(hex) {{
    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {{
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }}
    return bytes;
}}

function toHex(bytes) {{
    return bytes.map(b => b.toString(16).padStart(2, '0')).join('');
}}

// AES-CBC decrypt
function decrypt(ciphertext, key, iv) {{
    const decipher = crypto.createDecipheriv('aes-128-cbc', Buffer.from(key), Buffer.from(iv));
    let decrypted = decipher.update(Buffer.from(ciphertext));
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    return decrypted;
}}

const a = toNumbers("{a}");
const b = toNumbers("{b}");
const c = toNumbers("{c}");

const decrypted = decrypt(c, a, b);
const cookie = toHex(Array.from(decrypted));
console.log(cookie);
'''
    
    try:
        result = subprocess.run(
            ['node', '-e', node_script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None

def upload_via_ftp(php_content, body_content):
    """Upload PHP and body to server"""
    ftp = FTP(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd('htdocs')
    
    ftp.storbinary('STOR auto-publish.php', BytesIO(php_content.encode('utf-8')))
    ftp.storbinary('STOR article_body.html', BytesIO(body_content.encode('utf-8')))
    
    ftp.quit()
    return True

def execute_via_http():
    """Execute the PHP file via HTTP, handling anti-bot challenge"""
    client = httpx.Client(verify=False, timeout=30, follow_redirects=True)
    
    # First request - get the anti-bot challenge
    resp = client.get(f"{SITE_URL}/auto-publish.php")
    
    # Check if we got the challenge
    if 'slowAES' in resp.text or '__test' in resp.text:
        # Solve the challenge using Node.js
        cookie_value = solve_challenge_with_node(resp.text)
        
        if cookie_value:
            # Set the cookie and retry
            client.cookies.set('__test', cookie_value)
            resp = client.get(f"{SITE_URL}/auto-publish.php")
            
            try:
                result = resp.json()
                return True, result
            except:
                return True, {"message": "Published (check site)"}
        
        return False, "Could not solve anti-bot challenge"
    
    # If we got a normal response
    try:
        result = resp.json()
        return True, result
    except:
        return True, {"message": "Published (check site)"}

def cleanup_ftp():
    """Remove temporary files from server"""
    try:
        ftp = FTP(FTP_HOST, timeout=15)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd('htdocs')
        ftp.delete('auto-publish.php')
        ftp.delete('article_body.html')
        ftp.quit()
    except:
        pass

def publish_article(filename):
    """Main publish function"""
    articles_dir = Path(__file__).parent.parent / "articles"
    filepath = articles_dir / filename
    
    if not filepath.exists():
        print(f"❌ Arquivo não encontrado: {filename}")
        return False
    
    # Read article
    content = filepath.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(content)
    
    title = frontmatter.get('title', '')
    slug = frontmatter.get('slug', '')
    meta_desc = frontmatter.get('meta_description', '')
    
    print(f"📝 Publicando: {title}")
    
    # Create PHP
    php_content = f'''<?php
$conn = new mysqli('{DB_HOST}', '{DB_USER}', '{DB_PASS}', '{DB_NAME}');
if ($conn->connect_error) {{ die(json_encode(array("success" => false, "error" => $conn->connect_error))); }}

$body = file_get_contents('article_body.html');
$body_escaped = $conn->real_escape_string($body);
$now = date('Y-m-d H:i:s');

$title_escaped = $conn->real_escape_string('{title}');
$slug_escaped = $conn->real_escape_string('{slug}');
$excerpt_escaped = $conn->real_escape_string('{meta_desc}');

$sql = "INSERT INTO {DB_PREFIX}posts (post_title, post_content, post_excerpt, post_status, post_name, post_type, post_date, post_date_gmt, comment_status, ping_status) VALUES ('$title_escaped', '$body_escaped', '$excerpt_escaped', 'publish', '$slug_escaped', 'post', '$now', '$now', 'open', 'open')";

$conn->query($sql);
$post_id = $conn->insert_id;

echo json_encode(array("success" => true, "post_id" => $post_id, "url" => "/?p=" . $post_id));

$conn->close();
?>'''
    
    # Upload via FTP
    print("📤 Enviando via FTP...")
    upload_via_ftp(php_content, body)
    
    # Try to execute via HTTP
    print("🌐 Executando...")
    success, result = execute_via_http()
    
    if success:
        print(f"✅ Publicado com sucesso!")
        print(f"   ID: {result.get('post_id', 'N/A')}")
        print(f"   URL: {SITE_URL}{result.get('url', '')}")
        cleanup_ftp()
        return True
    else:
        print(f"⚠️  {result}")
        print(f"   Acesse manualmente: {SITE_URL}/auto-publish.php")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 publish_auto.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    success = publish_article(filename)
    sys.exit(0 if success else 1)
