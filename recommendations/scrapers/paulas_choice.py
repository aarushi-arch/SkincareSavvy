import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

BASE = "https://www.paulaschoice.com"

CATEGORY_URLS = {
    "cleansers": "/skincare/cleansers/",
    "moisturizers": "/skincare/moisturizers/",
    "serums": "/skincare/serums/",
    "toners": "/skincare/toners/",
    "exfoliants": "/skincare/exfoliants/",
    "sunscreens": "/skincare/sunscreen/",
    "eye-creams": "/skincare/eye-care/",
    "masks": "/skincare/masks/",
}

class PaulasChoiceScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

    def scrape_category(self, category, max_products=None):
    if category not in CATEGORY_URLS:
        return []

    collected = {}
    page = 1

    try:
        while True:
            url = BASE + CATEGORY_URLS[category] + f"?page={page}"
            self.driver.get(url)
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            links = soup.find_all("a", href=True)
            page_products = 0

            for a in links:
                href = a["href"]

                # ✅ STRICT Paula's Choice product URLs
                if not re.match(r"^/[^/]+/\d+\.html$", href):
                    continue

                full_url = BASE + href

                raw_name = a.get_text(" ", strip=True)

                # Clean name
                JUNK_PHRASES = ["shop now", "new", "sale"]
                name = raw_name
                for junk in JUNK_PHRASES:
                    name = name.replace(junk, "").replace(junk.title(), "").strip()

                # Skip garbage
                BAD_KEYWORDS = [
                    "affiliate", "privacy", "policy",
                    "terms", "reward", "program"
                ]

                if any(bad in name.lower() for bad in BAD_KEYWORDS):
                    continue

                if full_url not in collected:
                    collected[full_url] = {
                        "url": full_url,
                        "name": name,
                        "product_id": href.split("/")[-1].replace(".html", ""),
                    }
                    page_products += 1

            if page_products == 0:
                break

            if max_products and len(collected) >= max_products:
                break

            page += 1

        return list(collected.values())[:max_products]

    finally:
        pass


    def scrape_product_details(self, url):
        self.driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        def text(selector):
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ""

        ingredients = []
        ing_section = soup.find("div", {"id": "ingredients"})
        if ing_section:
            ingredients = [
                li.get_text(strip=True)
                for li in ing_section.find_all("li")
            ]

        return {
            "description": text("div.product-description"),
            "how_to_use": text("div.how-to-use"),
            "size": text("span.product-size"),
            "ingredients_list": ingredients,
            "skin_types": [],
            "skin_concerns": [],
        }

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass
