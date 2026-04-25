"""
CSV Product Enrichment
======================
Scrapes description, how_to_use, size from product_url in the CSV
and writes back to the same CSV file.

Usage:
    python enrich_csv_products.py                  # all rows
    python enrich_csv_products.py --limit 50       # first 50
    python enrich_csv_products.py --skip-filled    # skip rows with description

Requirements:
    pip install requests beautifulsoup4 pandas
"""

import re
import time
import random
import argparse
import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

CSV_PATH = "recommendations/notebooks/updated_products_with_images_npr.csv"
BACKUP   = "recommendations/notebooks/updated_products_with_images_npr.bak.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.debug("Request error: %s", e)
    return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ── LookFantastic ─────────────────────────────────────────────────────────────

def scrape_lookfantastic(url: str) -> dict:
    soup = _get(url)
    if not soup:
        return {}

    data: dict = {}

    # ── Description from JSON-LD ProductGroup.hasVariant ─────────────────────
    import json as _json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = _json.loads(script.string)
            items = [ld] if isinstance(ld, dict) else (ld if isinstance(ld, list) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                # ProductGroup → hasVariant[0].description (richest source)
                if item.get("@type") == "ProductGroup":
                    variants = item.get("hasVariant", [])
                    if variants and isinstance(variants[0], dict):
                        desc = variants[0].get("description", "")
                        if desc:
                            data["description"] = _clean(desc)
                            break
                # Plain Product
                if item.get("description") and "description" not in data:
                    data["description"] = _clean(item["description"])
            if "description" in data:
                break
        except Exception:
            pass

    # ── How to use — look for a tab/accordion section in HTML ─────────────────
    # LookFantastic renders product tabs as hidden divs
    for sel in [
        "[data-tab='directions']",
        "[data-tab='how-to-use']",
        "[id*='howToUse']",
        "[id*='directions']",
        "[class*='howToUse']",
        "[class*='directions']",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = _clean(el.get_text(" "))
            if len(txt) > 20:
                data["how_to_use"] = txt[:400]
                break

    # Fallback: search for "Directions" heading in page text
    if "how_to_use" not in data:
        full_text = soup.get_text(" ")
        m = re.search(
            r"(?:Directions?|How to use|Application)[:\s]+(.{30,400}?)(?:\n\n|\Z)",
            full_text, re.IGNORECASE | re.DOTALL
        )
        if m:
            data["how_to_use"] = _clean(m.group(1))[:400]

    # ── Size from title ───────────────────────────────────────────────────────
    title = soup.select_one("h1")
    if title:
        m = re.search(r"(\d+\s*(?:ml|g|oz))", title.get_text(), re.I)
        if m:
            data["size"] = m.group(1).strip()

    return data


# ── Paula's Choice ────────────────────────────────────────────────────────────

def scrape_paulaschoice(url: str) -> dict:
    soup = _get(url)
    if not soup:
        return {}

    data: dict = {}

    for sel in [".product-description", "[itemprop='description']"]:
        el = soup.select_one(sel)
        if el:
            data["description"] = _clean(el.get_text(" "))[:500]
            break

    for sel in [".how-to-use", "[class*='how-to-use']"]:
        el = soup.select_one(sel)
        if el:
            data["how_to_use"] = _clean(el.get_text(" "))[:300]
            break

    title = soup.select_one("h1")
    if title:
        m = re.search(r"(\d+\s*(?:ml|g|oz))", title.get_text(), re.I)
        if m:
            data["size"] = m.group(1).strip()

    return data


# ── Dispatcher ────────────────────────────────────────────────────────────────

SCRAPERS = {
    "www.lookfantastic.com": scrape_lookfantastic,
    "www.paulaschoice.com":  scrape_paulaschoice,
}


def scrape_url(url: str) -> dict:
    domain = urlparse(url).netloc
    scraper = SCRAPERS.get(domain)
    return scraper(url) if scraper else {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main(limit: int | None, skip_filled: bool) -> None:
    log.info("Loading CSV: %s", CSV_PATH)
    df = pd.read_csv(CSV_PATH)

    # Add columns if missing — use object dtype to avoid float64 incompatibility
    for col in ["description", "how_to_use", "size"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    # Filter
    if skip_filled:
        mask = df["description"].fillna("").str.len() == 0
        df_work = df[mask].copy()
        log.info("Rows with no description: %d", len(df_work))
    else:
        df_work = df.copy()

    if limit:
        df_work = df_work.head(limit)

    log.info("Scraping %d rows...", len(df_work))

    updated = 0
    for idx, row in df_work.iterrows():
        url = row.get("product_url", "")
        if not url or not url.startswith("http"):
            continue

        log.info("  [%d] %s", idx, url[:70])

        data = scrape_url(url)
        if not data:
            log.info("    No data")
            time.sleep(random.uniform(0.5, 1.0))
            continue

        # Write back to df — use pd.isna to handle NaN correctly
        changed = False
        for field, value in data.items():
            current = df.at[idx, field]
            if value and (pd.isna(current) or str(current).strip() == ""):
                df.at[idx, field] = value
                changed = True

        if changed:
            updated += 1
            log.info("    Saved: %s", list(data.keys()))
        else:
            log.info("    Nothing new to save")
        time.sleep(random.uniform(1.0, 2.5))

    # Backup + save
    df.to_csv(BACKUP, index=False)
    df.to_csv(CSV_PATH, index=False)

    log.info("\nBackup: %s", BACKUP)
    log.info("Saved:  %s", CSV_PATH)
    log.info("Updated: %d rows", updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",       type=int, default=None, help="Max rows to process")
    parser.add_argument("--skip-filled", action="store_true",    help="Skip rows with description")
    args = parser.parse_args()

    main(limit=args.limit, skip_filled=args.skip_filled)
