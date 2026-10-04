import ssl
# Disable SSL verification
ssl._create_default_https_context = ssl._create_unverified_context

import sys
import ftplib
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path('.env')
load_dotenv(dotenv_path=env_path)

FTP_HOST = os.environ.get('FTP_HOST', 'ftpupload.net')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')
SITE = "https://techtips.dpdns.org"
NOVO = SITE

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def ftp_with_retry(func, *args, **kwargs):
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(f"FTP attempt {i+1} failed: {e}")
            if i == 2:
                raise
            time.sleep(2)
    return None

def main():
    log("Connecting to FTP...")
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    log("Logged in.")
    
    try:
        # Step 1: Ensure plugins directory is renamed to plugins_disabled
        log("Step 1: Ensure plugins directory is renamed to plugins_disabled")
        ftp_with_retry(ftp.cwd, '/techtips.dpdns.org/htdocs/wp-content')
        log(f"Current dir: {ftp.pwd()}")
        try:
            ftp.size('plugins')
            log("Found 'plugins' directory, renaming to 'plugins_disabled'...")
            ftp.rename('plugins', 'plugins_disabled')
            log("Renamed plugins to plugins_disabled")
        except Exception as e:
            log(f"Could not rename plugins: {e}")
            # Maybe it's already renamed or not present
            pass
        
        # Step 2: Go to htdocs directory
        log("Step 2: Go to htdocs directory")
        ftp_with_retry(ftp.cwd, '/techtips.dpdns.org/htdocs')
        log(f"Current dir: {ftp.pwd()}")
        
        # Step 3: Check if migration script exists, if not upload it
        log("Step 3: Check for migration script")
        script_name = '_migra_urls.php'
        try:
            ftp.size(script_name)
            log(f"Found {script_name}, skipping upload")
        except Exception:
            log(f"{script_name} not found, uploading...")
            # Prepare the migration script
            log("Preparing migration script...")
            PHP_TEMPLATE = """<?php
header('Content-Type: text/plain');
define('WP_USE_THEMES', false);
require_once __DIR__ . '/wp-load.php';
global $wpdb;
$antigo = 'https://tech-tips.ct.ws';
$novo = '%NOVO%';

echo "== ANTES ==\\n";
foreach (array('siteurl', 'home') as $opt) {
    echo "$opt: " . get_option($opt) . "\\n";
}
$cont_ctws = $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_content LIKE '%tech-tips.ct.ws%' OR guid LIKE '%tech-tips.ct.ws%'");
$cont_guid = $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE guid LIKE '%tech-tips.ct.ws%'");
echo "posts com ct.ws (content+guid): $cont_ctws\\n";

// 1. siteurl/home
$wpdb->query($wpdb->prepare(
    "UPDATE {$wpdb->options} SET option_value = %s WHERE option_name IN ('siteurl', 'home')",
    $novo
));
echo "== siteurl/home atualizados ==\\n";

// 2. search-replace nos posts (content + guid)
$wpdb->query("UPDATE {$wpdb->posts} SET post_content = REPLACE(post_content, '$antigo', '$novo')");
$wpdb->query("UPDATE {$wpdb->posts} SET guid = REPLACE(guid, '$antigo', '$novo')");
echo "== search-replace em posts feito ==\\n";

// 3. postmeta (links internos em meta, se houver)
$wpdb->query("UPDATE {$wpdb->postmeta} SET meta_value = REPLACE(meta_value, '$antigo', '$novo') WHERE meta_value LIKE '%tech-tips.ct.ws%'");
echo "== postmeta varrido ==\\n";

// 4. options (pode ter URLs absolutas em widgets/tema)
$wpdb->query("UPDATE {$wpdb->options} SET option_value = REPLACE(option_value, '$antigo', '$novo') WHERE option_value LIKE '%tech-tips.ct.ws%'");
echo "== options varridas ==\\n";

echo "== DEPOIS ==\\n";
foreach (array('siteurl', 'home') as $opt) {
    echo "$opt: " . get_option($opt) . "\\n";
}
$resto = $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_content LIKE '%tech-tips.ct.ws%' OR guid LIKE '%tech-tips.ct.ws%'");
echo "posts ainda com ct.ws: $resto\\n";
echo "FIM\\n";
@unlink(__FILE__);
?>
"""
            PHP = PHP_TEMPLATE.replace('%NOVO%', NOVO)
            # Write to a temporary file
            tmp_php = Path('/tmp/migra_urls.php')
            tmp_php.write_text(PHP, encoding='utf-8')
            log(f"Wrote migration script to {tmp_php}")
            
            # Upload the file
            log(f"Uploading {script_name}...")
            with open(tmp_php, 'rb') as f:
                ftp.storbinary(f'STOR {script_name}', f)
            log(f"Uploaded {script_name}.")
        
        # Step 4: Execute the migration script via HTTP with anti-bot handling
        log("Step 4: Execute migration script via HTTP")
        # Add the scripts directory to sys.path
        sys.path.insert(0, 'scripts')
        # Now import antibot
        from antibot import get_pagina
        # Override SITE in antibot module
        import antibot
        antibot.SITE = SITE
        
        url = f"{SITE}/{script_name}"
        log(f"Fetching {url} with antibot...")
        html = get_pagina(url)
        log("Response received:")
        print(html)
        
    finally:
        # Step 5: Rename plugins_disabled back to plugins
        log("Step 5: Renaming plugins_disabled back to plugins")
        try:
            ftp_with_retry(ftp.cwd, '/techtips.dpdns.org/htdocs/wp-content')
            log(f"Current dir: {ftp.pwd()}")
            try:
                ftp.size('plugins_disabled')
                log("Renaming plugins_disabled back to plugins...")
                ftp.rename('plugins_disabled', 'plugins')
                log("Renamed back to plugins")
            except Exception as e:
                log(f"Could not rename plugins_disabled back: {e}")
        except Exception as e:
            log(f"Error in cleanup: {e}")
        ftp.quit()
        log("FTP connection closed.")

if __name__ == '__main__':
    main()
