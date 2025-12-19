import os
import sys
from pathlib import Path
import time
import django
import requests
from bs4 import BeautifulSoup

# Ensure project root is on sys.path so `SkincareSavvy.settings` can be imported
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from recommendations.models import Product

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_image_from_og(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            return meta.get("content")
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None


def _source_url(product: Product) -> str | None:
    return product.inci_decoder_url or product.product_url


def update_images_for_all_products():
    products = Product.objects.all()
    updated_count = 0
    for product in products:
        if product.image_url:
            continue
        src = _source_url(product)
        if not src:
            print(f"No source URL for: {product.name}")
            time.sleep(0.2)
            continue
        img_url = get_image_from_og(src)
        if img_url:
            product.image_url = img_url
            product.save(update_fields=["image_url"])
            updated_count += 1
            print(f"Updated image for: {product.name}")
        else:
            print(f"No image found for: {product.name}")
        time.sleep(1)
    print(f"Total images updated: {updated_count}")


if __name__ == "__main__":
    update_images_for_all_products()
