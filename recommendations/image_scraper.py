import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def scrape_image_from_incidecoder(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        img = soup.find("img", class_="product-image__img")
        if not img or not img.get("src"):
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                return og["content"]
            link = soup.find("link", rel="image_src")
            if link and link.get("href"):
                return link["href"]
        src = img["src"] if img else None
        if not src:
            return None
        return urljoin(url, src)
    except Exception:
        return None


def get_product_page_url(product) -> str | None:
    return product.inci_decoder_url or product.product_url


def update_missing_images(queryset, delay_seconds: float = 1.0) -> int:
    updated = 0
    for product in queryset:
        if product.image_url:
            continue
        page_url = get_product_page_url(product)
        if not page_url:
            continue
        img_url = scrape_image_from_incidecoder(page_url)
        if img_url:
            product.image_url = img_url
            product.save(update_fields=["image_url"])
            updated += 1
        time.sleep(delay_seconds)
    return updated
