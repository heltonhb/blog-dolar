import httpx, os, sys
sys.path.insert(0, "/home/helton/blog-dolar/dashboard")
from app import _wp_upload_media
WP_USER = os.environ.get('WP_USER', '')
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', '')
os.environ["SITE_URL"] = "https://tech-tips.byethost4.com"
result = _wp_upload_media(b"fake_bytes", "test_file.png", "Test Image")
print("UPLOAD RESULT:", result)
