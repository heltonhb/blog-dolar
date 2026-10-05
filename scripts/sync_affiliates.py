#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_affiliates.py — Sincronização automatizada de afiliados com o WordPress.
Executável tanto via CLI quanto pelo botão de manutenção do Dashboard.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from affiliate_manager import check_wp, get_amazon_tag, inject_wp  # noqa: E402


def main():
    try:
        tag = get_amazon_tag()
    except Exception as e:
        print(f"❌ Erro de configuração: {e}")
        sys.exit(1)

    print(f"=== SINCRONIZANDO AFILIADOS AMAZON (TAG: {tag}) ===")
    updated = inject_wp(tag)
    print(f"\nTotal de posts atualizados: {updated}")

    print("\n=== AUDITORIA DE CONFORMIDADE NO WORDPRESS ===")
    ok = check_wp(tag)
    if ok:
        print("\n✅ Todos os posts com links da Amazon estão 100% em conformidade!")
    else:
        print("\n⚠️ Alguns posts precisam de atenção. Verifique os logs acima.")


if __name__ == "__main__":
    main()
