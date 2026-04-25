"""
Product Detail Scraper
======================
Scrapes description, how_to_use, size, rating, review_count, and image_url
from each Product.product_url in the database and saves back to the DB.

Supports:
  - www.lookfantastic.com
  - www.paulaschoice.com

Usage:
    python scrape_product_details.py                  # all products
    python scrape_product_details.py --limit 50       # first 50
    python scrape_product_details.py --domain lookfantastic
    python scrape_product_details.py --skip-existing  # skip already-filled rows

Requirements:
    pip install requests beautifulsoup4
"""

import os
import sys
import re
import time
import random
import argparse
import logging
from urllib.parse import urlparse

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import requests
from bs4 import BeautifulSoup
from recommendations.models import Product

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            log.warning("HTTP %s for %s", r.status_code, url)
        except requests.RequestException as e:
            log.warning("Request error (%d): %s", attempt + 1, e)
        time.sleep(random.uniform(1.5, 3.0))
    return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ── LookFantastic scraper ─────────────────────────────────────────────────────

def scrape_lookfantastic(url: str) -> dict:
    soup = _get(url)
    if not soup:
        return {}

    data: dict = {}

    # Description — main product description block
    for sel in [
        "[data-component='product-description']",
        ".productDescription",
        "#product-description",
        "[class*='productDescription']",
        "[class*='product-description']",
    ]:
        el = soup.select_one(sel)
        if el:
            data["description"] = _clean(el.get_text(" "))
            break

    # How to use
    for sel in [
        "[data-component='how-to-use']",
        ".productHowToUse",
        "[class*='howToUse']",
        "[class*='how-to-use']",
    ]:
        el = soup.select_one(sel)
        if el:
            data["how_to_use"] = _clean(el.get_text(" "))
            break

    # Rating
    rating_el = soup.select_one("[data-review-average], [class*='reviewStars'] [class*='average']")
    if rating_el:
        m = re.search(r"(\d+\.\d+)", rating_el.get_text())
        if m:
            data["rating"] = float(m.group(1))

    # Review count
    count_el = soup.select_one("[data-review-count], [class*='reviewCount']")
    if count_el:
        m = re.search(r"(\d+)", count_el.get_text())
        if m:
            data["review_count"] = int(m.group(1))

    # Image
    img = soup.select_one(
        "img[class*='productImage'], img[class*='product-image'], "
        "[class*='productGallery'] img, [class*='product-gallery'] img"
    )
    if img:
        src = img.get("src") or img.get("data-src", "")
        if src.startswith("http"):
            data["image_url"] = src

    # Size — look for weight/volume in the title or breadcrumb
    title_el = soup.select_one("h1")
    if title_el:
        m = re.search(r"(\d+\s*(?:ml|g|oz|fl oz|mg))", title_el.get_text(), re.I)
        if m:
            data["size"] = m.group(1).strip()

    return data


# ── Paula's Choice scraper ────────────────────────────────────────────────────

def scrape_paulaschoice(url: str) -> dict:
    soup = _get(url)
    if not soup:
        return {}

    data: dict = {}

    # Description
    for sel in [
        ".product-description",
        "[class*='product-description']",
        ".pdp-description",
        "[itemprop='description']",
    ]:
        el = soup.select_one(sel)
        if el:
            data["description"] = _clean(el.get_text(" "))
            break

    # How to use
    for sel in [".how-to-use", "[class*='how-to-use']", "[class*='howToUse']"]:
        el = soup.select_one(sel)
        if el:
            data["how_to_use"] = _clean(el.get_text(" "))
            break

    # Rating
    rating_el = soup.select_one("[class*='rating-value'], [itemprop='ratingValue']")
    if rating_el:
        m = re.search(r"(\d+\.\d+)", rating_el.get_text())
        if m:
            data["rating"] = float(m.group(1))

    # Review count
    count_el = soup.select_one("[itemprop='reviewCount'], [class*='review-count']")
    if count_el:
        m = re.search(r"(\d+)", count_el.get_text())
        if m:
            data["review_count"] = int(m.group(1))

    # Image
    img = soup.select_one(
        "img[class*='product'], [class*='product-image'] img, "
        "[class*='pdp-image'] img"
    )
    if img:
        src = img.get("src") or img.get("data-src", "")
        if src.startswith("http"):
            data["image_url"] = src

    # Size
    title_el = soup.select_one("h1")
    if title_el:
        m = re.search(r"(\d+\s*(?:ml|g|oz|fl oz|mg))", title_el.get_text(), re.I)
        if m:
            data["size"] = m.group(1).strip()

    return data


# ── Dispatcher ────────────────────────────────────────────────────────────────

SCRAPERS = {
    "www.lookfantastic.com": scrape_lookfantastic,
    "www.paulaschoice.com":  scrape_paulaschoice,
}


def scrape_product(url: str) -> dict:
    domain = urlparse(url).netloc
    scraper = SCRAPERS.get(domain)
    if not scraper:
        log.debug("No scraper for domain: %s", domain)
        return {}
    return scraper(url)


# ── Main runner ───────────────────────────────────────────────────────────────

def run(limit: int | None, domain_filter: str | None, skip_existing: bool) -> None:
    qs = Product.objects.exclude(product_url__isnull=True).exclude(product_url="")

    if domain_filter:
        qs = qs.filter(product_url__icontains=domain_filter)

    if skip_existing:
        # Skip products that already have a description
        qs = qs.filter(description="")

    if limit:
        qs = qs[:limit]

    total = qs.count()
    log.info("Products to scrape: %d", total)

    updated = 0
    failed  = 0

    for i, product in enumerate(qs, 1):
        log.info("[%d/%d] %s", i, total, product.product_url[:80])

        try:
            data = scrape_product(product.product_url)
        except Exception as e:
            log.error("  Error: %s", e)
            failed += 1
            continue

        if not data:
            log.info("  No data extracted")
            failed += 1
            time.sleep(random.uniform(0.5, 1.5))
            continue

        # Update only non-empty fields — never overwrite existing data with blank
        changed = False
        for field, value in data.items():
            if value and not getattr(product, field, None):
                setattr(product, field, value)
                changed = True

        if changed:
            product.save()
            updated += 1
            log.info("  Saved: %s", list(data.keys()))
        else:
            log.info("  Nothing new to save")

        time.sleep(random.uniform(1.0, 2.5))

    log.info("\nDone. Updated: %d | Failed/skipped: %d | Total: %d", updated, failed, total)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape product details from DB URLs")
    parser.add_argument("--limit",         type=int,  default=None,  help="Max products to process")
    parser.add_argument("--domain",        type=str,  default=None,  help="Filter by domain substring (e.g. lookfantastic)")
    parser.add_argument("--skip-existing", action="store_true",      help="Skip products that already have a description")
    args = parser.parse_args()

    run(
        limit=args.limit,
        domain_filter=args.domain,
        skip_existing=args.skip_existing,
    )
