import httpx, os, sys
sys.path.insert(0, "/home/helton/blog-dolar/dashboard")
from app import _wp_upload_media
os.environ["WP_USER"] = "heltonhb"
os.environ["WP_APP_PASSWORD"] = "918v Nsaf GZio JLX7 Tk7n 3KZY"
os.environ["SITE_URL"] = "https://tech-tips.byethost4.com"
result = _wp_upload_media(b"fake_bytes", "test_file.png", "Test Image")
print("UPLOAD RESULT:", result)
