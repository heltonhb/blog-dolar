#!/usr/bin/env python3
"""
Instalar Ad Inserter via FTP no WordPress
"""

import ftplib
import zipfile
import requests
import io
from pathlib import Path

# Config FTP
FTP_HOST = 'ftpupload.net'
FTP_USER = 'b4_42799195'
FTP_PASS = 'Picard170!'

# URL do plugin Ad Inserter (última versão estável)
ADINSERTER_URL = 'https://downloads.wordpress.org/plugin/ad-inserter.2.8.4.zip'

def download_plugin():
    """Baixa o plugin Ad Inserter"""
    print("[1/3] Baixando Ad Inserter...")
    try:
        resp = requests.get(ADINSERTER_URL, timeout=60)
        if resp.status_code == 200:
            print(f"  ✓ Downloaded: {len(resp.content)} bytes")
            return resp.content
        else:
            print(f"  ✗ Erro: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return None

def upload_plugin(plugin_data):
    """Faz upload do plugin via FTP"""
    print("\n[2/3] Conectando ao FTP...")
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=15)
        ftp.login(FTP_USER, FTP_PASS)
        print("  ✓ Conectado!")
        
        # Navegar para plugins
        ftp.cwd('htdocs/wp-content/plugins')
        print("  ✓ Navegou para wp-content/plugins")
        
        # Extrair e fazer upload
        print("\n[3/3] Instalando plugin...")
        with zipfile.ZipFile(io.BytesIO(plugin_data)) as zf:
            # Listar arquivos
            files = zf.namelist()
            print(f"  Arquivos: {len(files)}")
            
            # Criar diretório do plugin
            plugin_dir = 'ad-inserter'
            try:
                ftp.mkd(plugin_dir)
                print(f"  ✓ Criou diretório: {plugin_dir}")
            except ftplib.error_perm:
                print(f"  → Diretório já existe: {plugin_dir}")
            
            # Upload de cada arquivo
            uploaded = 0
            for filename in files:
                if filename.endswith('/'):
                    # Criar diretório
                    dirpath = f"{plugin_dir}/{filename[:-1]}"
                    try:
                        ftp.mkd(dirpath)
                    except ftplib.error_perm:
                        pass
                else:
                    # Upload arquivo
                    try:
                        data = zf.read(filename)
                        remote_path = f"{plugin_dir}/{filename}"
                        
                        # Garantir que o diretório pai existe
                        parent = '/'.join(remote_path.split('/')[:-1])
                        try:
                            ftp.mkd(parent)
                        except:
                            pass
                        
                        ftp.storbinary(f'STOR {remote_path}', io.BytesIO(data))
                        uploaded += 1
                        if uploaded % 10 == 0:
                            print(f"    Upload: {uploaded}/{len(files)} arquivos...")
                    except Exception as e:
                        print(f"    Erro ao enviar {filename}: {e}")
            
            print(f"  ✓ Upload concluído: {uploaded} arquivos")
        
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"  ✗ Erro FTP: {e}")
        return False

def main():
    print("=" * 50)
    print("  INSTALADOR AD INSERTER - BLOG EM DOLAR")
    print("=" * 50)
    print()
    
    # Baixar plugin
    plugin_data = download_plugin()
    if not plugin_data:
        print("\n✗ Falha ao baixar o plugin")
        return
    
    # Upload via FTP
    if upload_plugin(plugin_data):
        print("\n" + "=" * 50)
        print("  ✓ AD INSERTER INSTALADO COM SUCESSO!")
        print("=" * 50)
        print()
        print("PRÓXIMOS PASSOS:")
        print("  1. Aguarde o site ficar online")
        print("  2. Acesse: https://tech-tips.byethost4.com/wp-admin")
        print("  3. Vá em Plugins > Plugins Instalados")
        print("  4. Ative o Ad Inserter")
        print("  5. Configure conforme SETUP-INSTRUCTIONS.txt")
    else:
        print("\n✗ Falha ao instalar o plugin")

if __name__ == "__main__":
    main()
