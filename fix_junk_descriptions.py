"""
Scrape and fix products that have junk descriptions (notable_effects lists)
or empty descriptions in the DB.

Usage:
    python fix_junk_descriptions.py
    python fix_junk_descriptions.py --limit 50
"""
import os, sys, re, time, random, json, argparse, logging
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")

import django
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


def _is_junk(desc):
    if not desc:
        return True
    d = str(desc).strip()
    return d.startswith("[") or d.startswith("'[") or len(d) < 50


def scrape_lookfantastic(url):
    soup = _get(url)
    if not soup:
        return {}
    data = {}

    # JSON-LD ProductGroup → hasVariant[0].description
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
                        if desc and len(desc) > 50:
                            data["description"] = _clean(desc)
                            break
                if item.get("description") and len(str(item["description"])) > 50:
                    data.setdefault("description", _clean(str(item["description"])))
            if "description" in data:
                break
        except Exception:
            pass

    # How to use — regex fallback on full page text
    if not data.get("how_to_use"):
        full = soup.get_text(" ")
        m = re.search(
            r"(?:Directions?|How to use|Application)[:\s]+(.{30,400}?)(?:\n\n|\Z)",
            full, re.IGNORECASE | re.DOTALL
        )
        if m:
            data["how_to_use"] = _clean(m.group(1))[:400]

    # Rating
    for sel in ["[data-review-average]", "[class*='reviewStars'] [class*='average']"]:
        el = soup.select_one(sel)
        if el:
            m = re.search(r"(\d+\.\d+)", el.get_text())
            if m:
                data["rating"] = float(m.group(1))
                break

    # Image
    img = soup.select_one("img[class*='productImage'], [class*='productGallery'] img")
    if img:
        src = img.get("src") or img.get("data-src", "")
        if src.startswith("http"):
            data["image_url"] = src

    return data


def scrape_paulaschoice(url):
    soup = _get(url)
    if not soup:
        return {}
    data = {}
    for sel in [".product-description", "[itemprop='description']"]:
        el = soup.select_one(sel)
        if el:
            txt = _clean(el.get_text(" "))
            if len(txt) > 50:
                data["description"] = txt
                break
    return data


SCRAPERS = {
    "www.lookfantastic.com": scrape_lookfantastic,
    "www.paulaschoice.com":  scrape_paulaschoice,
}


def run(limit):
    from urllib.parse import urlparse

    # Get all products with junk or empty descriptions
    qs = Product.objects.exclude(product_url__isnull=True).exclude(product_url="")
    targets = [p for p in qs if _is_junk(p.description)]
    log.info("Products needing fix: %d", len(targets))

    if limit:
        targets = targets[:limit]

    updated = 0
    for i, product in enumerate(targets, 1):
        url = product.product_url
        domain = urlparse(url).netloc
        scraper = SCRAPERS.get(domain)

        if not scraper:
            log.debug("[%d] No scraper for %s", i, domain)
            continue

        log.info("[%d/%d] %s", i, len(targets), url[:70])
        data = scraper(url)

        if not data.get("description"):
            log.info("  No description found")
            time.sleep(random.uniform(0.5, 1.0))
            continue

        changed_fields = []
        if data.get("description") and len(data["description"]) > 50:
            product.description = data["description"]
            changed_fields.append("description")

        if data.get("how_to_use") and not product.how_to_use:
            product.how_to_use = data["how_to_use"]
            changed_fields.append("how_to_use")

        if data.get("rating") and not product.rating:
            product.rating = data["rating"]
            changed_fields.append("rating")

        if data.get("image_url") and not product.image_url:
            product.image_url = data["image_url"]
            changed_fields.append("image_url")

        if changed_fields:
            product.save(update_fields=changed_fields)
            updated += 1
            log.info("  Saved: %s", changed_fields)

        time.sleep(random.uniform(1.0, 2.5))

    log.info("\nDone. Updated: %d / %d", updated, len(targets))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(args.limit)
