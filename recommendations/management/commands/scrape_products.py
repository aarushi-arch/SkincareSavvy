"""Django management command to scrape skincare products from INCI Decoder."""
import random
import time
from typing import List

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations.models import Product, Ingredient
from recommendations.scraping_utils import parse_ingredient_li


class Command(BaseCommand):
    help = "Scrape skincare products from INCI Decoder URLs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--urls",
            type=str,
            nargs="+",
            required=False,
            help="List of INCI Decoder URLs to scrape",
        )
        parser.add_argument(
            "--from-index",
            type=str,
            default=None,
            help="Crawl product URLs starting from an index page (e.g., https://incidecoder.com/products)",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=1,
            help="Maximum number of index pages to crawl when using --from-index",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of product URLs to scrape",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="Delay between requests in seconds (default: 2.0)",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="Request timeout in seconds (default: 10)",
        )

    def handle(self, *args, **options):
        urls = options.get("urls") or []
        from_index = options.get("from_index")
        max_pages = options.get("max_pages")
        limit = options.get("limit")
        delay = options["delay"]
        timeout = options["timeout"]
        
        if not urls and not from_index:
            raise CommandError("Provide --urls or --from-index to specify products to scrape.")
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        if from_index:
            collected = []
            base = "https://incidecoder.com"
            next_url = from_index
            pages_crawled = 0
            while next_url and pages_crawled < max_pages:
                try:
                    resp = session.get(next_url, timeout=timeout)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/products/") and href != "/products":
                            full = base + href
                            collected.append(full)
                        elif href.startswith("https://incidecoder.com/products/") and href != "https://incidecoder.com/products":
                            collected.append(href)
                    seen = set()
                    unique = []
                    for u in collected:
                        if u not in seen:
                            seen.add(u)
                            unique.append(u)
                    collected = unique
                    next_link = None
                    candidates = []
                    for a in soup.find_all("a", href=True):
                        txt = a.get_text(strip=True).lower()
                        if txt in ("next", "older"):
                            candidates.append(a["href"])
                        if a.get("rel") and "next" in a.get("rel"):
                            candidates.append(a["href"])
                    if candidates:
                        href = candidates[0]
                        next_url = href if href.startswith("http") else base + href
                    else:
                        next_url = None
                except Exception:
                    break
                pages_crawled += 1
                if pages_crawled < max_pages:
                    time.sleep(delay)
            if limit:
                collected = collected[:limit]
            urls = collected
        
        self.stdout.write(f"Starting to scrape {len(urls)} product(s)...")
        
        scraped = 0
        failed = 0
        
        session = session
        
        for url in urls:
            try:
                self.stdout.write(f"\nProcessing: {url}")
                
                # Fetch the page
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Extract product information
                # Try to find product name
                name = None
                name_elem = (
                    soup.find("h1") or
                    soup.find("h2", class_="product-name") or
                    soup.find("div", class_="product-title")
                )
                if name_elem:
                    name = name_elem.get_text(strip=True)
                
                # Try to find brand
                brand = None
                brand_elem = (
                    soup.find("span", class_="brand") or
                    soup.find("div", class_="brand-name") or
                    soup.find("a", class_="brand-link")
                )
                if brand_elem:
                    brand = brand_elem.get_text(strip=True)
                
                # Try to find category
                category = None
                category_elem = (
                    soup.find("span", class_="category") or
                    soup.find("div", class_="product-category")
                )
                if category_elem:
                    category = category_elem.get_text(strip=True)
                
                # If name not found, try to extract from URL or page title
                if not name:
                    title_tag = soup.find("title")
                    if title_tag:
                        name = title_tag.get_text(strip=True)
                    else:
                        # Fallback: use URL as name
                        name = url.split("/")[-1].replace("-", " ").title()
                
                # Extract ingredients
                ingredients = []
                
                # Primary method: look for li.ingred-bar elements
                for li in soup.select("li.ingred-bar"):
                    ing = parse_ingredient_li(li)
                    if ing and ing.get("ingredient"):
                        ingredients.append(ing)
                
                # Fallback: if no li.ingred-bar, try another pattern
                if not ingredients:
                    # Try to find a block with an ingredients string
                    block = soup.find(
                        lambda tag: tag.name in ["p", "div"]
                        and "ingredients" in (tag.get_text(" ", strip=True).lower())
                    )
                    
                    if block:
                        # Naive split on commas — not perfect but better than nothing
                        text = block.get_text(" ", strip=True)
                        # Try to find substring starting at 'ingredients:'
                        idx = text.lower().find("ingredients:")
                        if idx != -1:
                            ing_text = text[idx + len("ingredients:"):].strip()
                            for part in ing_text.split(","):
                                name_ing = part.strip()
                                if name_ing:
                                    ingredients.append({
                                        "ingredient": name_ing,
                                        "function": None,
                                        "label": None,
                                    })
                
                # Save to DB (update or create)
                try:
                    with transaction.atomic():
                        prod, created = Product.objects.update_or_create(
                            inci_decoder_url=url,
                            defaults={
                                "brand": brand or "",
                                "name": name or "Unknown Product",
                                "category": category or "",
                                "ingredients_json": ingredients,
                            },
                        )
                        
                        # Optional: create Ingredient rows
                        for ing in ingredients:
                            ing_name = ing.get("ingredient")
                            if not ing_name:
                                continue
                            Ingredient.objects.get_or_create(
                                name=ing_name,
                                defaults={
                                    "function": ing.get("function"),
                                    "label": ing.get("label"),
                                }
                            )
                        
                        scraped += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Saved: {prod} (created={created})"
                            )
                        )
                except Exception as exc:
                    self.stderr.write(f"✗ DB save failed for {url}: {exc}")
                    failed += 1
                
            except requests.RequestException as e:
                self.stderr.write(f"✗ Request failed for {url}: {e}")
                failed += 1
            except Exception as e:
                self.stderr.write(f"✗ Error processing {url}: {e}")
                failed += 1
            
            # Be polite between product page requests
            if url != urls[-1]:  # Don't sleep after the last URL
                sleep_time = delay + random.random() * 0.5
                time.sleep(sleep_time)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"Scraping finished!\n"
                f"Total scraped: {scraped}\n"
                f"Failed: {failed}\n"
                f"{'='*60}"
            )
        )

