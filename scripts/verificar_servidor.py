#!/usr/bin/env python3
"""
Verificar se o servidor ByetHost está online e executar configuração
Execute: python3 scripts/verificar_servidor.py
"""

import httpx
import time
import sys
from ftplib import FTP

SITE_URL = "https://tech-tips.byethost4.com"
FTP_HOST = "ftpupload.net"
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')

def check_server():
    """Verifica se o servidor está respondendo"""
    try:
        client = httpx.Client(verify=False, timeout=10)
        resp = client.get(f"{SITE_URL}/debug.php")
        return resp.status_code == 200, resp.text
    except Exception as e:
        return False, str(e)

def check_ftp():
    """Verifica se o FTP está funcionando"""
    try:
        ftp = FTP(FTP_HOST, timeout=10)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd('htdocs')
        files = []
        ftp.retrlines('LIST', files.append)
        ftp.quit()
        return True, len(files)
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("  VERIFICANDO SERVIDOR BYETHOST")
    print("=" * 60)
    
    # Verificar FTP
    print("\n[1/2] Verificando FTP...")
    ftp_ok, ftp_info = check_ftp()
    if ftp_ok:
        print(f"  ✅ FTP OK - {ftp_info} arquivos em htdocs/")
    else:
        print(f"  ❌ FTP offline: {ftp_info}")
        return False
    
    # Verificar HTTP
    print("\n[2/2] Verificando HTTP/HTTPS...")
    http_ok, http_info = check_server()
    if http_ok:
        print(f"  ✅ HTTP OK - WordPress carregando!")
        print(f"\n  Conteúdo debug.php:")
        print(f"  {http_info[:200]}...")
        return True
    else:
        print(f"  ❌ HTTP offline: {http_info[:100]}")
        print(f"\n  O servidor está instável. FTP funciona mas HTTP não.")
        print(f"  Isso é comum no ByetHost. Aguarde alguns minutos e tente novamente.")
        return False

if __name__ == "__main__":
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        print(f"\n--- Tentativa {attempt}/{max_attempts} ---")
        if main():
            print("\n" + "=" * 60)
            print("  SERVIDOR ONLINE! Próximos passos:")
            print("  1. Acesse: https://tech-tips.byethost4.com/debug.php")
            print("  2. Se WordPress carregar, acesse wp-admin")
            print("  3. Ative o plugin Ad Inserter")
            print("  4. Execute: https://tech-tips.byethost4.com/config-ad-cash.php")
            print("=" * 60)
            break
        else:
            if attempt < max_attempts:
                print(f"\nAguardando 30 segundos antes da próxima tentativa...")
                time.sleep(30)
            else:
                print("\n" + "=" * 60)
                print("  SERVIDOR CONTINUA OFFLINE")
                print("  Tente novamente mais tarde ou verifique o painel ByetHost")
                print("=" * 60)
