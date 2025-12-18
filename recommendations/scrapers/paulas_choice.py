import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

BASE = "https://www.paulaschoice.com"

CATEGORY_URLS = {
    "cleansers": "/skin-care-products/cleansers",
    "moisturizers": "/skin-care-products/moisturizers",
    "serums": "/skin-care-products/serums",
    "toners": "/skin-care-products/toners",
    "exfoliants": "/skin-care-products/exfoliants",
    "sunscreens": "/skin-care-products/sunscreen",
    "eye-creams": "/skin-care-products/eye-cream",
    "masks": "/skin-care-products/face-masks",
}


class PaulasChoiceScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless=new") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

    def scrape_category(self, category, max_products=None):
        if category not in CATEGORY_URLS:
            return []

        url = BASE + CATEGORY_URLS[category]
        print(f"Opening page: {url}")
        self.driver.get(url)
        time.sleep(5)  # wait for JS to load

        # Scroll to load all products if max_products is not small
        # Simple infinite scroll simulation
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # Wait for page to load

            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # Try to find "Load More" button and click it if exists
                try:
                    load_more = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Load More')]")
                    load_more.click()
                    time.sleep(3)
                except:
                    break # No load more, and scrolling didn't help
            last_height = new_height
            
            # If we have enough products (rough check), we can stop scrolling early if max_products is set
            if max_products:
                 # Count current products
                 current_count = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href$='.html']"))
                 if current_count >= max_products * 2: # heuristic buffer
                     break

        # find product links - User's selector was a[href*='/products/'], but actual site uses .html suffix with ID
        # Adapting to actual site structure while keeping Selenium approach
        product_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href$='.html']")

        collected = {}
        
        for p in product_links:
            href = p.get_attribute("href")
            if not href:
                continue
            
            # Verify it looks like a product URL (ends in /digits.html)
            # e.g. https://www.paulaschoice.com/resist-optimal-results-hydrating-cleanser/760.html
            if not re.search(r'/\d+\.html$', href):
                continue

            if href in collected:
                continue

            # Attempt to get a name
            name = p.get_text() if hasattr(p, 'get_text') else p.text
            if not name:
                name = p.get_attribute("aria-label") or ""
            if not name:
                 # Fallback to URL slug
                 parts = href.strip('/').split('/')
                 # part before ID is the name slug usually
                 if len(parts) >= 2:
                     name = parts[-2].replace('-', ' ').title()
                 else:
                     name = "Unknown Product"

            # Clean name (remove price info if stuck to it)
            # The text often contains newlines with price, e.g. "Name\nCurrent Price..."
            if '\n' in name:
                name = name.split('\n')[0]
            
            name = name.strip()
            
            # Product ID
            try:
                product_id = href.split('/')[-1].replace('.html', '')
            except:
                continue

            collected[href] = {
                "url": href,
                "name": name,
                "product_id": product_id,
                "price": None,
                "image": None,
                "rating": None,
                "review_count": 0
            }

            if max_products and len(collected) >= max_products:
                break

        return list(collected.values())

    def scrape_product_details(self, url):
        self.driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        
        # 1. Try to extract from JSON-LD Schema (Reliable for Rating, Name, Desc)
        import json
        schema_data = {}
        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            try:
                data = json.loads(s.get_text())
                if isinstance(data, dict) and data.get("@type") == "Product":
                    schema_data = data
                    break
            except:
                continue

        # Extract Rating from Schema
        rating = None
        review_count = 0
        if "aggregateRating" in schema_data:
            ar = schema_data["aggregateRating"]
            rating = ar.get("ratingValue")
            review_count = ar.get("reviewCount", 0)
            
        # Fallback Rating from HTML if Schema failed
        if rating is None:
            # Try finding aria-label="X out of 5 stars"
            stars = soup.find(attrs={"aria-label": re.compile(r"out of 5 stars", re.IGNORECASE)})
            if stars:
                try:
                    val = stars["aria-label"].split("out of")[0].strip()
                    rating = float(val)
                except:
                    pass

        # Extract Ingredients
        # Strategy: Find "Ingredients" header (h2/h3), then look for next ul/li
        ingredients = []
        
        # Try to find header by text - strict on tags to avoid nav menu
        headers = soup.find_all(["h2", "h3"], string=re.compile("Ingredients", re.IGNORECASE))
        for h in headers:
            # Traverse siblings to find a list
            curr = h
            found_list = False
            for _ in range(5): # Look ahead 5 elements
                curr = curr.find_next()
                if not curr:
                    break
                if curr.name == "ul":
                    # This might be the ingredient list
                    items = [li.get_text(strip=True) for li in curr.find_all("li")]
                    # Sanity check: Real ingredient lists usually start with common chemicals or "Water"
                    # The nav menu starts with "AHA", "Azelaic Acid", etc.
                    # If the list looks like a sorted glossary, skip it.
                    if items and items[0] in ["AHA", "Azelaic Acid", "Bakuchiol"]:
                        continue
                        
                    if items:
                        ingredients = items
                        found_list = True
                        break
            if found_list:
                break
        
        # Fallback: look for class containing "IngredientList"
        if not ingredients:
            ing_list_ul = soup.find("ul", class_=re.compile("IngredientList", re.IGNORECASE))
            if ing_list_ul:
                ingredients = [li.get_text(strip=True) for li in ing_list_ul.find_all("li")]

        def text(selector):
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ""

        description = schema_data.get("description") or text("div.product-description") or text("meta[name='description']")

        return {
            "description": description,
            "how_to_use": text("div.how-to-use"), # might need update but low priority
            "size": text("span.product-size"), # might need update
            "ingredients_list": ingredients,
            "rating": rating,
            "review_count": review_count,
            "skin_types": [],
            "skin_concerns": [],
        }

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass
