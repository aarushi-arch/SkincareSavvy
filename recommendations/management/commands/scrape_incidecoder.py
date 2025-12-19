"""Django management command to scrape skincare products from INCI Decoder."""
import csv
import os
import random
import time
from typing import List

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations.models import Product, Ingredient

class Command(BaseCommand):
    help = "Scrape skincare products from INCI Decoder"

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
            "--start-page",
            type=int,
            default=1,
            help="Page number to start crawling from (default: 1)",
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
        start_page = options.get("start_page")
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
            
            for page_num in range(start_page, start_page + max_pages):
                if page_num == 1:
                    next_url = from_index
                else:
                    # Handle existing query params
                    if "?" in from_index:
                        # If page param already exists, replace it (simple heuristic)
                        if "page=" in from_index:
                            # This is a bit complex to replace safely without regex or parsing, 
                            # but assuming user provides base url like .../products
                            pass 
                        else:
                            next_url = f"{from_index}&page={page_num}"
                    else:
                        next_url = f"{from_index}?page={page_num}"
                
                try:
                    self.stdout.write(f"Crawling index page {page_num}: {next_url}")
                    resp = session.get(next_url, timeout=timeout)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, "html.parser")
                    
                    found_on_page = 0
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/products/") and href != "/products":
                            full = base + href
                            collected.append(full)
                            found_on_page += 1
                        elif href.startswith("https://incidecoder.com/products/") and href != "https://incidecoder.com/products":
                            collected.append(href)
                            found_on_page += 1
                    
                    self.stdout.write(f"Found {found_on_page} products on this page.")
                    
                    # Be nice
                    time.sleep(delay)
                    
                except Exception as e:
                    self.stderr.write(f"Error crawling index page {page_num}: {e}")
                    # If page fails, maybe stop? Or continue?
                    # Continue might be safer if just one page times out
                    continue
            
            # Deduplicate
            seen = set()
            unique = []
            for u in collected:
                if u not in seen:
                    seen.add(u)
                    unique.append(u)
            collected = unique
            
            if limit:
                collected = collected[:limit]
            urls = collected
        
        self.stdout.write(f"Starting to scrape {len(urls)} product(s)...")
        
        # Prepare CSV file
        csv_file_path = os.path.join(settings.BASE_DIR, "recommendations", "products_with_ingredients.csv")
        
        # Check and update CSV header if needed
        fieldnames = ["Name", "Price", "Category", "Ingredients", "Rating"]
        existing_names = set()

        if os.path.isfile(csv_file_path):
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    header = []
            
            # If header doesn't match roughly (ignoring case), or missing Category
            if "Category" not in header and "category" not in header:
                self.stdout.write("Updating CSV structure to include Category...")
                # Read all data
                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    # Handle case where header might be Name,Price,Rating,Ingredients
                    # DictReader uses the first row as fieldnames
                    rows = list(reader)
                
                # Rewrite with new fieldnames
                with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in rows:
                        # Map old keys to new keys if necessary, or just rely on shared names
                        # Old: Name, Price, Rating, Ingredients
                        # New: Name, Price, Category, Ingredients, Rating
                        # We need to fill missing 'Category'
                        row['Category'] = row.get('Category', 'Unknown')
                        # Ensure all new fields exist
                        for field in fieldnames:
                            if field not in row:
                                row[field] = None
                        writer.writerow(row)
                        if row.get('Name'):
                            existing_names.add(row['Name'])
            else:
                # Just read existing names to avoid duplicates
                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Name'):
                            existing_names.add(row['Name'])
        else:
            # Create new
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        
        scraped = 0
        failed = 0
        
        for url in urls:
            try:
                self.stdout.write(f"\nProcessing: {url}")
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                
                # --- NEW EXTRACTION LOGIC ---
                try:
                    # ✅ Product Name
                    name_elem = soup.select_one("h1.product-title")
                    if not name_elem:
                        name_elem = soup.find("h1") # Fallback
                    
                    if name_elem:
                        name = name_elem.text.strip()
                    else:
                        name = "Unknown Product"
                    
                    # ✅ Brand (best academic approach)
                    brand = name.split(" ")[0] if name else ""

                    # ✅ Category (Try breadcrumbs)
                    category = "Unknown"
                    breadcrumbs = soup.select(".breadcrumbs a")
                    if breadcrumbs:
                        # Usually Home > Products > Category > Product
                        # Or Home > Brands > Brand > Product
                        # Let's take the second to last link if available
                        if len(breadcrumbs) >= 2:
                             # Check if it looks like a category (not Home or Products root)
                            candidate = breadcrumbs[-1].text.strip()
                            if candidate.lower() not in ["home", "products"]:
                                category = candidate
                    
                    # ✅ Price (Not typically available on INCIDecoder)
                    price = None
                    
                    # ✅ Rating (Not available on INCIDecoder)
                    rating = None

                    # ✅ Ingredients (CORRECT)
                    ingredients_list = [
                        a.text.strip()
                        for a in soup.select("div.ingredlist-short-like-section a")
                    ]
                    
                    # Debug output
                    self.stdout.write(f"Name: {name}")
                    self.stdout.write(f"Brand: {brand}")
                    self.stdout.write(f"Category: {category}")
                    self.stdout.write(f"Ingredients: {ingredients_list[:5]}... (Total: {len(ingredients_list)})")
                    
                except Exception as e:
                    self.stderr.write(f"Extraction error for {url}: {e}")
                    failed += 1
                    continue
                # -----------------------------
                
                # Convert string ingredients to dicts for model compatibility
                ingredients_json = [
                    {"ingredient": ing, "function": None, "label": None}
                    for ing in ingredients_list
                ]

                # Save to DB
                with transaction.atomic():
                    prod, created = Product.objects.update_or_create(
                        inci_decoder_url=url,
                        defaults={
                            "brand": brand,
                            "name": name,
                            "category": category,
                            "price": price,
                            "rating": rating,
                            "ingredients_json": ingredients_json,
                        },
                    )
                    for ing_name in ingredients_list:
                        if not ing_name:
                            continue
                        Ingredient.objects.get_or_create(name=ing_name)
                
                # Save to CSV
                if name not in existing_names:
                    with open(csv_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([name, price, category, ", ".join(ingredients_list), rating])
                    existing_names.add(name) # Update in-memory set
                    csv_action = "and CSV"
                else:
                    csv_action = "(CSV skipped)"

                scraped += 1
                action = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"  ✓ {action} in DB {csv_action}"))
                
                # Be nice to the server
                time.sleep(delay)
                
            except Exception as e:
                self.stderr.write(f"Error processing {url}: {e}")
                failed += 1
            
            if url != urls[-1]:
                time.sleep(delay + random.random() * 0.5)
        
        self.stdout.write(self.style.SUCCESS(f"\nScraping finished! Total: {scraped}, Failed: {failed}"))
