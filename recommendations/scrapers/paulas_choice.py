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
    "serums": "/skin-care-products/face-serums",
    "toners": "/skin-care-products/toners",
    "exfoliants": "/skin-care-products/exfoliants",
    "sunscreens": "/skin-care-products/sunscreen",
    "eye-creams": "/skin-care-products/eye-creams",
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
        # Robust infinite scroll and Load More handling
        print("  Starting auto-scroll and load more...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        no_change_count = 0
        
        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # Wait for page to load
            
            # Check for "Load More" buttons
            clicked_load_more = False
            try:
                # Try multiple common selectors for Load More buttons
                load_more_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view more')]")
                
                for btn in load_more_buttons:
                    if btn.is_displayed():
                        print("  Clicking 'Load More' button...")
                        self.driver.execute_script("arguments[0].click();", btn)
                        clicked_load_more = True
                        time.sleep(3)
                        break
            except Exception as e:
                # print(f"  Load more click error: {e}")
                pass

            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height and not clicked_load_more:
                no_change_count += 1
                if no_change_count >= 2: # Stop if height hasn't changed for 2 iterations and no button clicked
                    print("  Reached end of page.")
                    break
            else:
                no_change_count = 0 # Reset if we moved or clicked
                
            last_height = new_height
            
            # If we have enough products (rough check), we can stop scrolling early if max_products is set
            if max_products:
                 # Count current products
                 current_count = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href$='.html']"))
                 if current_count >= max_products * 2: # heuristic buffer
                     break

        # find product links - User's selector was a[href*='/products/'], but actual site uses .html suffix with ID
        # Adapting to actual site structure while keeping Selenium approach
        
        # Find product cards
        cards = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'ProductTileStudioOnestyles__Wrapper')]")
        
        collected = {}
        
        for card in cards:
            href = card.get_attribute("href")
            if not href:
                continue
            
            # Verify it looks like a product URL (ends in /digits.html)
            if not re.search(r'/\d+\.html$', href):
                continue

            if href in collected:
                continue

            # Scroll into view to ensure text is rendered (crucial for lazy loaded text)
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                # Small sleep to allow render
                # time.sleep(0.1) 
            except:
                pass

            # Extract info from card
            card_text = card.text
            if not card_text:
                # Fallback to textContent if text is empty (hidden)
                card_text = card.get_attribute("textContent")
            
            # Name extraction
            name = "Unknown Product"
            image_url = None
            price = None
            
            try:
                img = card.find_element(By.TAG_NAME, "img")
                image_url = img.get_attribute("src")
                # Title often has the name
                name_cand = img.get_attribute("title")
                if name_cand:
                    name = name_cand
            except:
                pass
            
            # If name is still generic or empty, parse text
            # Example text: "AWARD WINNER\nRESIST\nOptimal Results Hydrating Cleanser\n$20.80\n$26.00\n310"
            if name == "Unknown Product" or not name:
                lines = [l.strip() for l in card_text.split('\n') if l.strip()]
                # Heuristic: Find first line starting with $ -> price. Line before is name.
                price_idx = -1
                for i, line in enumerate(lines):
                    if '$' in line:
                        price_idx = i
                        break
                
                if price_idx > 0:
                    name = lines[price_idx - 1]
                elif lines:
                    # Fallback: finding longest line that doesn't look like a badge
                    candidates = [l for l in lines if len(l) > 10 and '$' not in l]
                    if candidates:
                        name = candidates[-1] # Usually the last text before price is the name
                    else:
                        name = lines[0]

            # Price extraction
            # Find first $ price in text
            prices = re.findall(r'\$(\d+\.\d+)', card_text)
            if prices:
                price = prices[0] # Use first price (usually sale price if present)
            
            # Product ID
            try:
                product_id = href.split('/')[-1].replace('.html', '')
            except:
                product_id = ""

            collected[href] = {
                "url": href,
                "name": name,
                "product_id": product_id,
                "price": price,
                "image": image_url,
                "rating": None, # Will get from details
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
