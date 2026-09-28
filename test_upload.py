"""Smoke test manual: upload de uma imagem fake para a biblioteca do WordPress.

Executar com: python test_upload.py

O corpo fica dentro de ``main()``/``__main__`` de propósito: o pytest importa
este arquivo durante a coleção (nome ``test_*.py``) e, antes disso, o código de
módulo estava sobrescrevendo ``SITE_URL`` com um domínio antigo e disparando uma
chamada de rede — o que quebrava outros testes da suíte.
"""
import os
import sys

WP_USER = os.environ.get("WP_USER", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")


def main():
    sys.path.insert(0, "/home/helton/blog-dolar/dashboard")
    from app import _wp_upload_media

    result = _wp_upload_media(b"fake_bytes", "test_file.png", "Test Image")
    print("UPLOAD RESULT:", result)


if __name__ == "__main__":
    main()
