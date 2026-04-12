"""
Purplle Sun Care Scraper
=========================
Uses Selenium (headless Chrome) to render JS pages, then BeautifulSoup to parse.

Scrapes: product_name, product_url, product_type, clean_ingreds,
         price, suitable_skin_types, notable_effects, image_url, rating

Usage:
    python scrape_purplle_suncare.py                   # 5 pages (~100 products)
    python scrape_purplle_suncare.py --pages 20
    python scrape_purplle_suncare.py --out out.csv

Requirements:
    pip install selenium beautifulsoup4 pandas webdriver-manager
"""

import argparse
import re
import time
import random
import logging
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

PRODUCT_TYPE  = "Sunscreen"
CATEGORY_URL  = "https://www.purplle.com/skin/sun-care"
BASE_URL      = "https://www.purplle.com"

# INR → NPR conversion rate
NPR_RATE = 1.6

SKIN_TYPE_MAP = {
    "dry":         "Dry",
    "oily":        "Oily",
    "combination": "Combination",
    "sensitive":   "Sensitive",
    "normal":      "Normal",
    "acne":        "Acne-prone",
    "all skin":    "Normal",
    "all types":   "Normal",
}

EFFECT_MAP = {
    "hydrat":      "Hydrating",
    "moistur":     "Hydrating",
    "brighten":    "Brightening",
    "glow":        "Brightening",
    "anti-ag":     "Anti-aging",
    "wrinkle":     "Anti-aging",
    "acne":        "Acne Control",
    "blemish":     "Acne Control",
    "barrier":     "Barrier Repair",
    "ceramide":    "Barrier Repair",
    "exfoliat":    "Exfoliating",
    "sooth":       "Soothing",
    "calm":        "Soothing",
    "spf":         "Sun Protection",
    "sun protect": "Sun Protection",
    "sunscreen":   "Sun Protection",
    "uv":          "Sun Protection",
    "pa+":         "Sun Protection",
    "de-tan":      "Brightening",
    "pigment":     "Brightening",
    "tan":         "Brightening",
}


# ── Driver ────────────────────────────────────────────────────────────────────

def make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    return webdriver.Chrome(options=opts)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_skin_types(text: str) -> list:
    t = text.lower()
    found = []
    for kw, label in SKIN_TYPE_MAP.items():
        if kw in t and label not in found:
            found.append(label)
    return found or ["Normal"]


def _infer_effects(text: str) -> list:
    t = text.lower()
    found = []
    for kw, label in EFFECT_MAP.items():
        if kw in t and label not in found:
            found.append(label)
    return found


def _parse_price(raw: str) -> str:
    digits = re.sub(r"[^\d.]", "", raw)
    if digits:
        try:
            npr = round(float(digits) * NPR_RATE)
            return f"NPR {npr:,}"
        except ValueError:
            pass
    return raw


def _scroll_to_bottom(driver, pause: float = 1.5):
    """Scroll down to trigger lazy-loaded products."""
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h


# ── Listing page: collect product URLs ───────────────────────────────────────

def get_product_urls(driver: webdriver.Chrome, max_pages: int = 5) -> list:
    """Scroll through category pages and collect product detail URLs."""
    urls = []
    seen = set()

    for page in range(1, max_pages + 1):
        page_url = f"{CATEGORY_URL}?page_no={page}" if page > 1 else CATEGORY_URL
        log.info("Listing page %d → %s", page, page_url)
        driver.get(page_url)

        # Wait for product cards to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/']"))
            )
        except Exception:
            log.warning("  Timeout waiting for products on page %d", page)

        _scroll_to_bottom(driver, pause=1.2)
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Collect all product links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/product/" in href:
                full = href if href.startswith("http") else BASE_URL + href
                # Strip query params
                full = full.split("?")[0]
                if full not in seen:
                    seen.add(full)
                    urls.append(full)

        log.info("  → %d unique product URLs so far", len(urls))

        # Check if there's a next page
        next_btn = soup.find("a", string=re.compile(r"next|›|»", re.I))
        if not next_btn and page > 1:
            log.info("  No next page found, stopping.")
            break

        time.sleep(random.uniform(1.5, 2.5))

    return urls


# ── Product detail page ───────────────────────────────────────────────────────

def scrape_product(driver: webdriver.Chrome, url: str) -> dict | None:
    """Scrape a single Purplle product page."""
    try:
        driver.get(url)
        # Wait for product name to load
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .product-name, [class*='product-title']"))
        )
        time.sleep(0.8)
    except Exception:
        log.debug("Timeout on %s", url)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # ── Name ──────────────────────────────────────────────────────────────────
    name = ""
    for sel in ["h1", "[class*='product-name']", "[class*='product-title']", "[class*='pdp-name']"]:
        tag = soup.select_one(sel)
        if tag:
            name = tag.get_text(strip=True)
            break
    if not name:
        # Fallback: extract from URL slug
        slug = url.rstrip("/").split("/product/")[-1]
        name = slug.replace("-", " ").title()

    # ── Price ─────────────────────────────────────────────────────────────────
    price = ""
    for sel in ["[class*='price']", "[class*='mrp']", "[class*='selling-price']"]:
        tag = soup.select_one(sel)
        if tag:
            raw = tag.get_text(strip=True)
            if "₹" in raw or re.search(r"\d{2,}", raw):
                price = _parse_price(raw)
                break
    if not price:
        m = re.search(r"₹\s*(\d[\d,]*)", page_text)
        if m:
            price = _parse_price(m.group(0))

    # ── Rating ────────────────────────────────────────────────────────────────
    rating = ""
    for sel in ["[class*='rating']", "[class*='stars']", "[class*='review-score']"]:
        tag = soup.select_one(sel)
        if tag:
            m = re.search(r"(\d+\.\d+)", tag.get_text())
            if m:
                rating = m.group(1)
                break
    if not rating:
        m = re.search(r"(\d\.\d)\s*/\s*5", page_text)
        if m:
            rating = m.group(1)

    # ── Image ─────────────────────────────────────────────────────────────────
    image_url = ""
    for sel in ["[class*='product-image'] img", "[class*='pdp-image'] img",
                "[class*='main-image'] img", "img[class*='product']"]:
        img = soup.select_one(sel)
        if img and img.get("src", "").startswith("http"):
            image_url = img["src"]
            break
    if not image_url:
        # Any image from ppl-media CDN
        img = soup.find("img", src=re.compile(r"ppl-media|purplle"))
        if img:
            image_url = img.get("src", "")

    # ── Ingredients ───────────────────────────────────────────────────────────
    ingredients = []
    ingred_section = ""

    # Look for an "Ingredients" section heading
    for tag in soup.find_all(["h2", "h3", "h4", "strong", "b", "span", "div"]):
        if re.search(r"ingredient", tag.get_text(), re.I):
            # Grab the next sibling or parent text
            nxt = tag.find_next_sibling()
            if nxt:
                ingred_section = nxt.get_text(" ", strip=True)
            else:
                parent = tag.parent
                if parent:
                    ingred_section = parent.get_text(" ", strip=True)
            if len(ingred_section) > 20:
                break

    if ingred_section:
        parts = re.split(r"[,;]", ingred_section)
        ingredients = [p.strip().lower() for p in parts if 2 < len(p.strip()) < 60]

    # ── Skin types & effects from full page text ──────────────────────────────
    skin_types = _infer_skin_types(page_text)
    effects    = _infer_effects(page_text)

    return {
        "product_name":        name,
        "product_url":         url,
        "product_type":        PRODUCT_TYPE,
        "clean_ingreds":       str(ingredients),
        "price":               price,
        "suitable_skin_types": str(skin_types),
        "notable_effects":     str(effects),
        "image_url":           image_url,
        "rating":              rating,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def scrape(max_pages: int = 5, output: str = "purplle_moisturizers.csv") -> pd.DataFrame:
    log.info("Starting Purplle scraper (headless Chrome) …")
    driver = make_driver()

    try:
        log.info("Step 1: Collecting product URLs from %d listing page(s) …", max_pages)
        product_urls = get_product_urls(driver, max_pages)
        log.info("Found %d unique product URLs.", len(product_urls))

        log.info("Step 2: Scraping product detail pages …")
        rows = []
        for i, url in enumerate(product_urls, 1):
            log.info("  [%d/%d] %s", i, len(product_urls), url.split("/product/")[-1][:60])
            row = scrape_product(driver, url)
            if row and row["product_name"]:
                rows.append(row)
            time.sleep(random.uniform(1.0, 2.0))

    finally:
        driver.quit()

    if not rows:
        log.error("No products scraped.")
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "product_name", "product_url", "product_type", "clean_ingreds",
        "price", "suitable_skin_types", "notable_effects", "image_url", "rating",
    ])
    df.drop_duplicates(subset=["product_name"], inplace=True)

    out_path = Path(output)
    df.to_csv(out_path, index=False)
    log.info("Saved %d products → %s", len(df), out_path)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Purplle sun care products")
    parser.add_argument("--pages", type=int, default=5,
                        help="Listing pages to scrape (default 5, ~100 products)")
    parser.add_argument("--out", type=str, default="purplle_suncare.csv",
                        help="Output CSV filename")
    args = parser.parse_args()

    df = scrape(max_pages=args.pages, output=args.out)
    if not df.empty:
        print(f"\nDone — {len(df)} sun care products saved to {args.out}")
        print(df[["product_name", "price", "rating"]].head(10).to_string(index=False))
