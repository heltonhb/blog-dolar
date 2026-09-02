#!/usr/bin/env python3
"""
Configuração completa de monetização - Blog em Dolar
Execute quando o servidor ByetHost estiver online

Passos:
1. Verifica se o site está acessível
2. Faz upload dos scripts de configuração
3. Executa config-ad-cash.php via HTTP
4. Verifica se os anúncios estão funcionando
"""

import httpx
import time
import sys
from ftplib import FTP
from io import BytesIO

# Configurações
SITE_URL = "https://tech-tips.byethost4.com"
FTP_HOST = "ftpupload.net"
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')
ADCASH_ZONE_ID = "suhf5fqztw"

def check_server():
    """Verifica se o servidor está respondendo"""
    try:
        client = httpx.Client(verify=False, timeout=15)
        resp = client.get(f"{SITE_URL}/debug.php")
        if resp.status_code == 200:
            return True, resp.text
        return False, f"Status: {resp.status_code}"
    except Exception as e:
        return False, str(e)

def upload_via_ftp(local_path, remote_path):
    """Upload arquivo via FTP"""
    try:
        ftp = FTP(FTP_HOST, timeout=15)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd('htdocs')
        
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        print(f"  Erro FTP: {e}")
        return False

def run_config_via_http():
    """Executa config-ad-cash.php via HTTP"""
    try:
        client = httpx.Client(verify=False, timeout=30)
        
        # Primeiro acesso (GET) para carregar o formulário
        resp = client.get(f"{SITE_URL}/config-ad-cash.php")
        
        if resp.status_code == 200:
            # POST para aplicar configuração
            data = {'config_adcash': '1'}
            resp = client.post(f"{SITE_URL}/config-ad-cash.php", data=data)
            
            if resp.status_code == 200:
                return True, resp.text
            else:
                return False, f"POST status: {resp.status_code}"
        else:
            return False, f"GET status: {resp.status_code}"
    except Exception as e:
        return False, str(e)

def verify_ads():
    """Verifica se os anúncios estão aparecendo"""
    try:
        client = httpx.Client(verify=False, timeout=15)
        resp = client.get(SITE_URL)
        
        content = resp.text.lower()
        
        # Verificar se código AdCash está presente
        has_adcash = 'acscdn.com/script/aclib.js' in content or 'aclib' in content
        has_zone = ADCASH_ZONE_ID in content
        
        return {
            'accessible': resp.status_code == 200,
            'has_adcash_script': has_adcash,
            'has_zone_id': has_zone,
            'content_length': len(resp.text)
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    print("=" * 60)
    print("  CONFIGURAÇÃO DE MONETIZAÇÃO - BLOG EM DOLAR")
    print("=" * 60)
    
    # Passo 1: Verificar servidor
    print("\n[1/5] Verificando servidor...")
    server_ok, server_info = check_server()
    if not server_ok:
        print(f"  ❌ Servidor offline: {server_info[:100]}")
        print("  Execute novamente quando o servidor estiver online.")
        return False
    print(f"  ✅ Servidor online!")
    
    # Passo 2: Upload scripts
    print("\n[2/5] Fazendo upload dos scripts...")
    scripts = [
        ("scripts/config-ad-cash.php", "config-ad-cash.php"),
        ("scripts/verificar-ad-inserter.php", "verificar-ad-inserter.php"),
    ]
    
    for local, remote in scripts:
        print(f"  Upload: {remote}...", end=" ")
        if upload_via_ftp(local, remote):
            print("✅")
        else:
            print("❌")
    
    # Passo 3: Verificar wp-admin
    print("\n[3/5] Verificando wp-admin...")
    try:
        client = httpx.Client(verify=False, timeout=15)
        resp = client.get(f"{SITE_URL}/wp-admin/")
        if resp.status_code in [200, 302]:
            print(f"  ✅ wp-admin acessível (status: {resp.status_code})")
        else:
            print(f"  ⚠️  wp-admin retornou status: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Erro ao acessar wp-admin: {e}")
    
    # Passo 4: Configurar Ad Inserter via HTTP
    print("\n[4/5] Configurando Ad Inserter com AdCash...")
    config_ok, config_result = run_config_via_http()
    if config_ok:
        print("  ✅ Configuração aplicada!")
        # Verificar se há mensagem de sucesso
        if 'sucesso' in config_result.lower() or 'success' in config_result.lower():
            print("  ✅ AdCash configurado com sucesso!")
        else:
            print(f"  ⚠️  Resposta: {config_result[:200]}")
    else:
        print(f"  ❌ Erro na configuração: {config_result[:200]}")
    
    # Passo 5: Verificar anúncios
    print("\n[5/5] Verificando se anúncios estão funcionando...")
    ads_info = verify_ads()
    
    if 'error' in ads_info:
        print(f"  ❌ Erro: {ads_info['error']}")
    else:
        print(f"  Site acessível: {'✅' if ads_info['accessible'] else '❌'}")
        print(f"  Script AdCash: {'✅' if ads_info['has_adcash_script'] else '❌'}")
        print(f"  Zone ID presente: {'✅' if ads_info['has_zone_id'] else '❌'}")
        print(f"  Tamanho da página: {ads_info['content_length']} chars")
    
    # Resumo
    print("\n" + "=" * 60)
    print("  RESUMO DA CONFIGURAÇÃO")
    print("=" * 60)
    print(f"  Site: {SITE_URL}")
    print(f"  AdCash Zone ID: {ADCASH_ZONE_ID}")
    print(f"  Status: {'✅ MONETIZAÇÃO ATIVA' if config_ok else '❌ PENDENTE'}")
    print()
    print("  Próximos passos:")
    print("  1. Acesse o site e verifique se os anúncios aparecem")
    print("  2. Acesse wp-admin > Settings > Ad Inserter para ajustes")
    print("  3. DELETE o arquivo config-ad-cash.php por segurança")
    print("  4. Monitore seus ganhos no painel AdCash")
    print("=" * 60)
    
    return config_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
