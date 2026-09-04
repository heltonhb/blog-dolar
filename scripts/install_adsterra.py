#!/usr/bin/env python3
"""Instala código do Adsterra no WordPress via FTP."""
import ftplib
import os
import sys
from pathlib import Path

# Carregar .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "b4_42799195")
FTP_PASS = os.environ.get("FTP_PASS", "")

def install_adsterra(code: str):
    """Instala código Adsterra no header.php do tema Astra."""
    if not FTP_PASS:
        print("❌ FTP_PASS não configurado no .env")
        return False
    
    print(f"📡 Conectando ao FTP...")
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd("htdocs/wp-content/themes/astra")
    
    # Download header.php
    with open("/tmp/header_adsterra.php", "wb") as f:
        ftp.retrbinary("RETR header.php", f.write)
    print("✅ header.php baixado")
    
    # Read
    with open("/tmp/header_adsterra.php", "r") as f:
        content = f.read()
    
    # Check if already installed
    if "adsterra" in content.lower():
        print("⚠️ Código Adsterra já está instalado")
        ftp.quit()
        return True
    
    # Add code before </head>
    if "</head>" in content:
        content = content.replace("</head>", f"{code}\n</head>", 1)
        
        # Upload
        with open("/tmp/header_adsterra_new.php", "w") as f:
            f.write(content)
        
        with open("/tmp/header_adsterra_new.php", "rb") as f:
            ftp.storbinary("STOR header.php", f)
        
        print("✅ Código Adsterra instalado no header.php")
    else:
        print("❌ Tag </head> não encontrada")
        ftp.quit()
        return False
    
    ftp.quit()
    return True

def remove_adsterra():
    """Remove código Adsterra do header.php."""
    if not FTP_PASS:
        print("❌ FTP_PASS não configurado no .env")
        return False
    
    print(f"📡 Conectando ao FTP...")
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd("htdocs/wp-content/themes/astra")
    
    # Download
    with open("/tmp/header_adsterra.php", "wb") as f:
        ftp.retrbinary("RETR header.php", f.write)
    
    with open("/tmp/header_adsterra.php", "r") as f:
        content = f.read()
    
    # Remove Adsterra code (anything between adsterra comments or script tags)
    import re
    # Remove script tags containing adsterra
    content = re.sub(r'<!-- Adsterra.*?-->.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*adsterra[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    
    with open("/tmp/header_adsterra_new.php", "w") as f:
        f.write(content)
    
    with open("/tmp/header_adsterra_new.php", "rb") as f:
        ftp.storbinary("STOR header.php", f)
    
    print("✅ Código Adsterra removido")
    ftp.quit()
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python install_adsterra.py install 'CODIGO_ADSTERRA'")
        print("  python install_adsterra.py remove")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "install":
        if len(sys.argv) < 3:
            print("❌ Forneça o código Adsterra como argumento")
            sys.exit(1)
        code = sys.argv[2]
        install_adsterra(code)
    elif action == "remove":
        remove_adsterra()
    else:
        print(f"❌ Ação desconhecida: {action}")
