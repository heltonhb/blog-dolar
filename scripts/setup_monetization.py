#!/usr/bin/env python3
"""
Script para configurar monetização no Blog em Dolar
Gera código de anúncios e pages obrigatórias para WordPress
"""

import json
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIGURAÇÕES
# ============================================================

ADCASH_AUTOTAG = """
<!-- AdCash Autotag - Cole no <head> do tema -->
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
<!-- Configuração do AdCash (descomente e ajuste após cadastro) -->
<script>
  // window.ADCASH_ALLOWED_FORMATS = ['banner', 'popup', 'interstitial'];
  // window.ADCASH_SITE_ID = 'SEU_SITE_ID_AQUI';
</script>
"""

ADSTERRA_CODE = """
<!-- Adsterra Social Bar -->
<script>
  (d, s, id) => {
    var js;
    if (d.getElementById(id)) return;
    js = d.createElement(s);
    js.id = id;
    js.src = 'https://strelnikoff.net/code/social-bar.js';
    d.getElementsByTagName('head')[0].appendChild(js);
  }(document, 'script', 'adsterra-social-bar');
</script>
"""

# ============================================================
# GERAÇÃO DE CÓDIGOS
# ============================================================

def generate_ad_codes():
    """Gera códigos de anúncios para diferentes posições"""
    
    codes = {
        "header_banner": """
<!-- Header Banner (728x90) - AdCash -->
<div id="adcash-header" style="text-align:center; margin:10px 0;">
  <script>
    // AdCash Banner - Substitua pelo código real após cadastro
    document.write('<div style="background:#f0f0f0; padding:20px; border:1px dashed #ccc;">');
    document.write('AdCash Banner 728x90 - Aguardando configuração');
    document.write('</div>');
  </script>
</div>
""",
        "sidebar_rectangle": """
<!-- Sidebar Rectangle (300x250) - AdCash -->
<div id="adcash-sidebar" style="margin:15px 0;">
  <script>
    // AdCash Rectangle - Substitua pelo código real após cadastro
    document.write('<div style="background:#f0f0f0; padding:20px; border:1px dashed #ccc; width:300px;">');
    document.write('AdCash Rectangle 300x250<br>Aguardando configuração');
    document.write('</div>');
  </script>
</div>
""",
        "in_content": """
<!-- In-Content Ad (728x90) - Após 2º parágrafo -->
<div id="adcash-content" style="text-align:center; margin:20px 0; clear:both;">
  <script>
    // AdCash In-Content - Substitua pelo código real após cadastro
    document.write('<div style="background:#e8f4f8; padding:15px; border:1px dashed #999;">');
    document.write('AdCash In-Content 728x90<br>Aguardando configuração');
    document.write('</div>');
  </script>
</div>
""",
        "footer_banner": """
<!-- Footer Banner (728x90) - AdCash -->
<div id="adcash-footer" style="text-align:center; margin:20px 0; border-top:1px solid #eee; padding-top:15px;">
  <script>
    // AdCash Footer - Substitua pelo código real após cadastro
    document.write('<div style="background:#f5f5f5; padding:15px; border:1px dashed #ccc;">');
    document.write('AdCash Footer 728x90<br>Aguardando configuração');
    document.write('</div>');
  </script>
</div>
"""
    }
    
    return codes

# ============================================================
# GERAÇÃO DE PÁGINAS OBRIGATÓRIAS
# ============================================================

def generate_privacy_policy():
    """Gera Privacy Policy para WordPress"""
    return f"""Privacy Policy for Blog em Dolar

Last Updated: {datetime.now().strftime('%B %d, %Y')}

Introduction
Welcome to Blog em Dolar ("we," "our," or "us"). We are committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website.

Information We May Collect
- Log Data: IP address, browser type, pages visited, time spent
- Cookies: Session cookies for site functionality
- Third-Party Ads: Our advertising partners may collect data

How We Use Your Information
- To operate and maintain our website
- To analyze usage and improve content
- To display relevant advertisements
- To comply with legal obligations

Third-Party Services
We use third-party advertising companies, including:
- AdCash (adcash.com)
- Google AdSense (future)

These companies may use cookies to serve ads based on your visits.

Your Rights
You have the right to:
- Access your personal data
- Request deletion of your data
- Opt-out of personalized advertising

Contact Us
If you have questions about this policy, contact us at:
- Email: privacy@tech-tips.byethost4.com

This Privacy Policy is generated for informational purposes and should be reviewed by a legal professional."""

def generate_about_us():
    """Gera About Us para WordPress"""
    return """About Blog em Dolar

Welcome to Blog em Dolar – your trusted source for technology tips, guides, and reviews in English, helping you navigate the digital world.

Our Mission
We believe technology should be accessible to everyone. Our goal is to provide clear, practical, and honest content that helps you make informed decisions about the tech tools you use every day.

What We Cover
- Digital Privacy & Security
- Cloud Computing & Storage
- Software Reviews & Tutorials
- Hardware Guides & Comparisons
- Productivity Tips & Tricks

Our Team
Blog em Dolar is created by a team of technology enthusiasts passionate about sharing knowledge and helping others succeed in the digital age.

Why Trust Us?
- Independent reviews and recommendations
- No paid placements without disclosure
- Regular updates with latest information
- Focus on practical, real-world solutions

Connect With Us
Have a question or suggestion? We'd love to hear from you!
- Email: hello@tech-tips.byethost4.com

Thank you for visiting Blog em Dolar!"""

def generate_terms():
    """Gera Terms of Service"""
    return f"""Terms of Service for Blog em Dolar

Last Updated: {datetime.now().strftime('%B %d, %Y')}

1. Acceptance of Terms
By accessing Blog em Dolar, you agree to these Terms of Service.

2. Content
All content is provided for informational purposes only. We make no warranties about the accuracy or completeness.

3. Intellectual Property
Content on this site is owned by Blog em Dolar or its content creators and is protected by copyright laws.

4. User Conduct
You agree not to:
- Use the site for illegal purposes
- Attempt to gain unauthorized access
- Interfere with site operations

5. Limitation of Liability
We are not liable for any damages arising from your use of this site.

6. Changes to Terms
We reserve the right to modify these terms at any time.

7. Contact
For questions about these terms, email: legal@tech-tips.byethost4.com"""

# ============================================================
# GERAÇÃO DE INSTRUÇÕES PARA WORDPRESS
# ============================================================

def generate_wordpress_instructions():
    """Gera instruções detalhadas para configurar no WordPress"""
    return """
============================================================
  INSTRUÇÕES PARA CONFIGURAR MONETIZAÇÃO NO WORDPRESS
============================================================

1. ACESSAR O WORDPRESS
   URL: https://tech-tips.byethost4.com/wp-admin
   Usuário: heltonhb
   Senha: (sua senha)

2. INSTALAR PLUGIN DE ANÚNCIOS
   a) Vá em Plugins > Adicionar Novo
   b) Pesquise: "Ad Inserter"
   c) Clique em "Instalar Agora" > "Ativar"
   
3. CONFIGURAR AD INSERTEE
   a) Vá em Settings > Ad Inserter
   b) Configure cada bloco:
   
   BLOCO 1 (Header):
   - Activation: ✅
   - Alignment: Center
   - Posts: Home, Posts
   - Pages: Static
   - Code:
     <div style="text-align:center; margin:10px 0;">
       <script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
     </div>
   
   BLOCO 2 (Sidebar):
   - Ative no widget area do tema
   
   BLOCO 3 (In-Content):
   - After paragraph: 2
   - Posts: ✅
   
   BLOCO 4 (Footer):
   - Before </body>
   
4. CRIAR PÁGINAS OBRIGATÓRIAS
   a) Vá em Pages > Adicionar Novo
   b) Crie:
      - Privacy Policy
      - About Us
      - Terms of Service
      - Contact
   
5. ADICIONAR PÁGINAS AO MENU
   a) Vá em Appearance > Menus
   b) Adicione as páginas criadas
   c) Salve o menu

6. CRIAR CONTA ADCASH
   a) Acesse: https://adcash.com/publishers/signup
   b) Cadastre-se com email real
   c) Adicione seu site
   d) Copie o código de rastreamento
   e) Cole no Ad Inserter (BLOCO 1)

7. TESTAR
   a) Visite o site
   b) Verifique se os anúncios aparecem
   c) Teste em mobile e desktop
   d) Verifique no console do navegador (F12)

============================================================
"""

# ============================================================
# SCRIPT PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("  CONFIGURADOR DE MONETIZAÇÃO - BLOG EM DOLAR")
    print("=" * 60)
    print()
    
    # Criar diretório de saída
    output_dir = Path("docs/monetization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Gerar códigos de anúncios
    print("[1/4] Gerando códigos de anúncios...")
    codes = generate_ad_codes()
    
    for name, code in codes.items():
        filepath = output_dir / f"ad_{name}.html"
        filepath.write_text(code.strip(), encoding='utf-8')
        print(f"  ✓ {filepath}")
    
    # 2. Gerar páginas obrigatórias
    print("\n[2/4] Gerando páginas obrigatórias...")
    pages = {
        "privacy-policy.md": generate_privacy_policy(),
        "about-us.md": generate_about_us(),
        "terms-of-service.md": generate_terms()
    }
    
    for filename, content in pages.items():
        filepath = output_dir / filename
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✓ {filepath}")
    
    # 3. Gerar instruções
    print("\n[3/4] Gerando instruções de configuração...")
    instructions = generate_wordpress_instructions()
    filepath = output_dir / "SETUP-INSTRUCTIONS.txt"
    filepath.write_text(instructions, encoding='utf-8')
    print(f"  ✓ {filepath}")
    
    # 4. Gerar resumo
    print("\n[4/4] Gerando resumo...")
    summary = {
        "generated_at": datetime.now().isoformat(),
        "files_created": list(output_dir.glob("*")),
        "next_steps": [
            "1. Verificar se o site está acessível",
            "2. Criar conta no AdCash",
            "3. Seguir instruções em SETUP-INSTRUCTIONS.txt",
            "4. Integrar códigos de anúncios",
            "5. Criar páginas obrigatórias",
            "6. Monitorar primeiros ganhos"
        ]
    }
    
    filepath = output_dir / "summary.json"
    filepath.write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
    print(f"  ✓ {filepath}")
    
    print("\n" + "=" * 60)
    print("  ARQUIVOS GERADOS EM: docs/monetization/")
    print("=" * 60)
    print()
    print("PRÓXIMOS PASSOS:")
    print("  1. Ler SETUP-INSTRUCTIONS.txt para instruções detalhadas")
    print("  2. Criar conta no AdCash: https://adcash.com/publishers/signup")
    print("  3. Seguir o passo a passo no WordPress")
    print()
    print("BOA MONETIZAÇÃO! 💰")
    print()

if __name__ == "__main__":
    main()
