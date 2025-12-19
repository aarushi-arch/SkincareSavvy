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
    """
    Scrapes the product image using the og:image meta tag.
    Returns the image URL or None if not found.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        meta_tag = soup.find("meta", property="og:image")
        if meta_tag and meta_tag.get("content"):
            return meta_tag.get("content")
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None


def _source_url(product: Product) -> str | None:
    # Prefer INCI Decoder URL if available, otherwise original product URL
    return product.inci_decoder_url or product.product_url


def update_missing_images():
    """
    Loops through all products with missing image_url (NULL or empty string)
    and updates them by scraping from their source_url.
    """
    missing_products = Product.objects.filter(image_url__isnull=True) | Product.objects.filter(image_url="")
    total = missing_products.count()
    print(f"Found {total} products missing images.")

    updated_count = 0
    for product in missing_products:
        src = _source_url(product)
        if src:
            img_url = get_image_from_og(src)
            if img_url:
                product.image_url = img_url
                product.save(update_fields=["image_url"])
                updated_count += 1
                print(f"[{updated_count}/{total}] Updated image for: {product.name}")
            else:
                print(f"[{updated_count}/{total}] No image found for: {product.name}")
        else:
            print(f"[{updated_count}/{total}] No source URL for: {product.name}")
        time.sleep(1)

    print(f"Done! Total images updated: {updated_count} / {total}")


if __name__ == "__main__":
    update_missing_images()
