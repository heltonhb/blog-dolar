#!/usr/bin/env python3
"""
Blog em Dolar - Instalador de Anuncios
Configura AdCash no WordPress automaticamente
"""

import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx


# Snippets do AdCash para WordPress
ADCASH_SNIPPET_HEADER = """
<!-- AdCash AutoTag - Nao remova -->
<script type="text/javascript" src="//cdn.adcash.com/advertisement/adcash.js"></script>
<!-- /AdCash AutoTag -->
""".strip()

ADCASH_SNIPPET_BODY = """
<!-- AdCash PopUnder -->
<script>
(function(){
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.async = true;
    s.src = '//cdn.adcash.com/advertisement/adcash.js';
    var x = document.getElementsByTagName('script')[0];
    x.parentNode.insertBefore(s, x);
})();
</script>
<!-- /AdCash PopUnder -->
""".strip()


class AdInserter:
    """Insere codigo de anuncios via WPCode plugin ou tema"""
    
    def __init__(self, wp_url: str, username: str, app_password: str):
        self.base_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2"
        self.auth = (username, app_password)
    
    def install_via_wpcode(self):
        """
        Instala via plugin WPCode (recomendado)
        Cria um snippet no Header & Footer
        """
        print("\n  Metodo: WPCode Plugin")
        print("  Instrucoes manuais (plugin gratuito):")
        print("  1. WP Plugins > Adicionar Novo > WPCode")
        print("  2. Ative o plugin")
        print("  3. Code Snippets > Add Snippet")
        print("  4. Select 'Add Custom Code'")
        print("  5. Cole o codigo do AdCash no campo 'Code Preview'")
        print("  6. Location: Site Wide Header")
        print("  7. Salve e ative")
        
        print("\n  Codigo para copiar (HEADER):")
        print("  " + "-" * 40)
        print(ADCASH_SNIPPET_HEADER)
        print("  " + "-" * 40)
    
    def install_via_theme(self):
        """
        Instala diretamente no tema via functions.php
        """
        print("\n  Metodo: functions.php")
        print("  Adicione este codigo no final do functions.php do tema:")
        print("  " + "-" * 40)
        
        code = f'''
// AdCash AutoTag - Header
add_action('wp_head', function() {{
    echo '{ADCASH_SNIPPET_HEADER}';
}});
'''
        print(code)
        print("  " + "-" * 40)
    
    def install_via_plugin_insert(self):
        """
        Instala via plugin Ad Inserter (alternativa)
        """
        print("\n  Metodo: Plugin Ad Inserter (gratuito)")
        print("  1. WP Plugins > Adicionar Novo > Ad Inserter")
        print("  2. Ative o plugin")
        print("  3. Settings > Ad Inserter")
        print("  4. Crie um novo bloco")
        print("  5. Cole o codigo do AdCash")
        print("  6. Ative o bloco")
        
        print("\n  Codigo para colar no bloco:")
        print("  " + "-" * 40)
        print(ADCASH_SNIPPET_HEADER)
        print("  " + "-" * 40)


def show_adcash_setup():
    """Mostra guia completo de setup do AdCash"""
    
    print("=" * 60)
    print("  SETUP ADCASH - Guia Passo a Passo")
    print("=" * 60)
    
    print("""
  PASSO 1: Criar conta no AdCash
  ─────────────────────────────
  1. Acesse: https://adcash.com
  2. Clique em 'Register'
  3. NAO use traducao do navegador!
  4. Preencha dados reais
  5. Valide pelo email

  PASSO 2: Adicionar seu site
  ────────────────────────────
  1. No painel, va em 'Sites'
  2. Clique 'Add Site'
  3. URL: https://seusite.com
  4. Vertical: Travel ou News
  5. Adult Content: DESMARCADO

  PASSO 3: Pegar o codigo
  ────────────────────────
  1. Va em 'Tags' ou 'Ad Tags'
  2. Crie uma nova tag
  3. Formato: Autotag (recomendado)
  4. Copie o codigo fornecido

  PASSO 4: Inserir no WordPress
  ──────────────────────────────
    """)
    
    inserter = AdInserter("", "", "")
    
    print("\n  Opcoes de insercao (escolha uma):")
    print("\n  [A] Plugin WPCode (mais facil)")
    inserter.install_via_wpcode()
    
    print("\n  [B] Plugin Ad Inserter")
    inserter.install_via_plugin_insert()
    
    print("\n  [C] functions.php do tema")
    inserter.install_via_theme()
    
    print("""
  PASSO 5: Configurar densidade
  ──────────────────────────────
  No painel AdCash:
  1. Va em 'Zones' ou 'Ad Zones'
  2. Configuracao de exibicao:
     - Balanced (recomendado)
     - Aggressive (mais lucro, pior UX)
     - Conservative (menos lucro, melhor UX)
  
  PASSO 6: Verificar funcionamento
  ─────────────────────────────────
  1. Abra seu site em aba anonima
  2. Verifique se anuncios aparecem
  3. Teste em mobile tambem
  4. Cheque o painel AdCash para impressions
    """)


if __name__ == "__main__":
    show_adcash_setup()
