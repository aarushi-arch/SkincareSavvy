"""
Scrape and fix products that have missing or junk descriptions in the DB.
Targets products where description is empty, <50 chars, or starts with '['.

Usage:
    python fix_bad_descriptions.py
    python fix_bad_descriptions.py --dry-run   # preview only
"""
import os, sys, re, time, random, json, argparse, logging
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import requests
from bs4 import BeautifulSoup
from recommendations.models import Product

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.debug("Error: %s", e)
    return None


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def scrape_lookfantastic(url):
    soup = _get(url)
    if not soup:
        return {}
    data = {}

    # Description from JSON-LD ProductGroup.hasVariant
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string)
            items = [ld] if isinstance(ld, dict) else (ld if isinstance(ld, list) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") == "ProductGroup":
                    variants = item.get("hasVariant", [])
                    if variants and isinstance(variants[0], dict):
                        desc = variants[0].get("description", "")
                        if desc:
                            data["description"] = _clean(desc)
                            break
                if item.get("description") and "description" not in data:
                    data["description"] = _clean(item["description"])
            if "description" in data:
                break
        except Exception:
            pass

    # How to use
    for sel in ["[data-tab='directions']", "[data-tab='how-to-use']",
                "[id*='howToUse']", "[class*='howToUse']"]:
        el = soup.select_one(sel)
        if el:
            txt = _clean(el.get_text(" "))
            if len(txt) > 20:
                data["how_to_use"] = txt[:400]
                break

    if "how_to_use" not in data:
        full = soup.get_text(" ")
        m = re.search(r"(?:Directions?|How to use|Application)[:\s]+(.{30,400}?)(?:\n\n|\Z)",
                      full, re.IGNORECASE | re.DOTALL)
        if m:
            data["how_to_use"] = _clean(m.group(1))[:400]

    # Rating
    for sel in ["[data-review-average]", "[class*='reviewStars'] [class*='average']",
                "[itemprop='ratingValue']"]:
        el = soup.select_one(sel)
        if el:
            m = re.search(r"(\d+\.\d+)", el.get_text())
            if m:
                data["rating"] = float(m.group(1))
                break

    # Size
    title = soup.select_one("h1")
    if title:
        m = re.search(r"(\d+\s*(?:ml|g|oz))", title.get_text(), re.I)
        if m:
            data["size"] = m.group(1).strip()

    return data


def scrape_paulaschoice(url):
    soup = _get(url)
    if not soup:
        return {}
    data = {}
    for sel in [".product-description", "[itemprop='description']"]:
        el = soup.select_one(sel)
        if el:
            data["description"] = _clean(el.get_text(" "))
            break
    for sel in [".how-to-use", "[class*='how-to-use']"]:
        el = soup.select_one(sel)
        if el:
            data["how_to_use"] = _clean(el.get_text(" "))[:400]
            break
    return data


SCRAPERS = {
    "www.lookfantastic.com": scrape_lookfantastic,
    "www.paulaschoice.com":  scrape_paulaschoice,
}


def needs_fix(p):
    d = str(p.description or "").strip()
    return not d or d.startswith("[") or d.startswith("'[") or len(d) < 50


def main(dry_run):
    from urllib.parse import urlparse

    products = [
        p for p in Product.objects.exclude(product_url__isnull=True).exclude(product_url="")
        if needs_fix(p)
    ]
    log.info("Products needing fix: %d", len(products))

    updated = failed = 0

    for i, product in enumerate(products, 1):
        url = product.product_url
        domain = urlparse(url).netloc
        scraper = SCRAPERS.get(domain)

        if not scraper:
            log.info("[%d/%d] No scraper for %s — skipping", i, len(products), domain)
            continue

        log.info("[%d/%d] %s", i, len(products), url[:80])

        if dry_run:
            log.info("  DRY RUN — would scrape")
            continue

        data = scraper(url)
        if not data or not data.get("description"):
            log.info("  No description found")
            failed += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        product.description = data["description"]
        if data.get("how_to_use") and not product.how_to_use:
            product.how_to_use = data["how_to_use"]
        if data.get("rating") and not product.rating:
            product.rating = data["rating"]
        if data.get("size") and not product.size:
            product.size = data["size"]

        product.save(update_fields=["description", "how_to_use", "rating", "size"])
        updated += 1
        log.info("  Saved: %s", data["description"][:80])
        time.sleep(random.uniform(1.0, 2.5))

    log.info("\nUpdated: %d | Failed: %d", updated, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
