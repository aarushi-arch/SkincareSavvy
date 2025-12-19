import requests
from bs4 import BeautifulSoup

def test_index_page():
    url = "https://incidecoder.com/products"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        product_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/products/") and href != "/products":
                product_links.append(href)
        
        print(f"Found {len(product_links)} product links on index page.")
        if product_links:
            print(f"Sample link: {product_links[0]}")
            return "https://incidecoder.com" + product_links[0]
    except Exception as e:
        print(f"Error fetching index: {e}")
    return None

def test_product_page(url):
    if not url:
        return
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"\nFetching product page: {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Inspect H1
        h1 = soup.find("h1")
        if h1:
            print(f"H1: {h1} Text: {h1.get_text(strip=True)}")
        
        # Look for brand links
        print("Searching for links starting with /brands/...")
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("/brands/"):
                print(f"Brand Link: {a['href']} Text: {a.get_text(strip=True)}")

        # Inspect ingredient section
        ing_div = soup.find("div", class_="ingredlist-short-like-section")
        if ing_div:
            print(f"Ingredient Section Text (first 200 chars): {ing_div.get_text(strip=True)[:200]}")
            # Check for links inside
            ing_links = ing_div.find_all("a")
            print(f"Found {len(ing_links)} links in ingredient section.")
            if ing_links:
                print(f"First ingredient link: {ing_links[0].get_text(strip=True)}")
        name_elem = (
            soup.find("h1") or
            soup.find("h2", class_="product-name") or
            soup.find("div", class_="product-title")
        )
        print(f"Name: {name_elem.get_text(strip=True) if name_elem else 'NOT FOUND'}")
        
        # Brand
        brand_elem = (
            soup.find("span", class_="brand") or
            soup.find("div", class_="brand-name") or
            soup.find("a", class_="brand-link")
        )
        print(f"Brand: {brand_elem.get_text(strip=True) if brand_elem else 'NOT FOUND'}")
        
        # Ingredients
        ingredients = soup.select("li.ingred-bar") # This selector relies on implementation details not fully visible here
        print(f"Found {len(ingredients)} ingredients via 'li.ingred-bar'.")
        
    except Exception as e:
        print(f"Error fetching product page: {e}")

if __name__ == "__main__":
    sample_product_url = test_index_page()
    if sample_product_url:
        test_product_page(sample_product_url)
