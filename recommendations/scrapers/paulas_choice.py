"""Scraper for Paula's Choice products."""
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class PaulasChoiceScraper:
    """Scraper for Paula's Choice products."""

    def __init__(self):
        self.base_url = "https://www.paulaschoice.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_category(self, category, max_products=None):
        """
        Scrape products from a category.

        Args:
            category: Category name (e.g., 'cleansers', 'moisturizers')
            max_products: Max products to scrape (None = all)

        Returns:
            List of product dicts
        """
        products = []
        page = 0
        url = f"{self.base_url}/skin-care-products/{category}"

        while True:
            print(f"Scraping page {page + 1}...")

            try:
                # Fetch page with pagination
                response = self.session.get(
                    url,
                    params={'start': page * 24, 'sz': 24},
                    timeout=15
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find product tiles
                tiles = (
                    soup.find_all('div', class_='product-tile') or
                    soup.find_all('div', {'data-itemid': True})
                )

                if not tiles:
                    break

                # Extract each product
                for tile in tiles:
                    product = self._extract_product(tile)
                    if product:
                        products.append(product)

                        if max_products and len(products) >= max_products:
                            return products

                # Check for next page
                if not soup.find('a', class_='next'):
                    break

                page += 1
                time.sleep(2)  # Rate limiting

            except Exception as e:
                print(f"Error: {e}")
                break

        return products

    def _extract_product(self, tile):
        """Extract product data from HTML tile."""
        try:
            data = {}

            # Name
            name_elem = tile.find('a', class_='product-name') or tile.find('h3')
            if not name_elem:
                return None
            data['name'] = name_elem.get_text(strip=True)

            # URL
            link = tile.find('a', href=True)
            if link:
                data['url'] = urljoin(self.base_url, link['href'])

            # Product ID
            data['product_id'] = (
                tile.get('data-itemid') or
                tile.get('data-product-id') or
                (data.get('url', '').split('/')[-1].replace('.html', '') if data.get('url') else None)
            )

            # Price
            price_elem = tile.find('span', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                match = re.search(r'\$?(\d+\.?\d*)', price_text)
                if match:
                    data['price'] = float(match.group(1))

            # Image
            img = tile.find('img')
            if img:
                data['image'] = img.get('src') or img.get('data-src')

            # Rating
            rating_elem = tile.find('div', class_='bv_main_container')
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '')
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    data['rating'] = float(match.group(1))

            # Review count
            review_elem = tile.find('span', class_='bv_numReviews_text')
            if review_elem:
                match = re.search(r'(\d+)', review_elem.get_text())
                if match:
                    data['review_count'] = int(match.group(1))

            return data

        except Exception as e:
            print(f"Error extracting: {e}")
            return None

    def scrape_product_details(self, url):
        """
        Scrape detailed info from product page.

        Args:
            url: Product page URL

        Returns:
            Dict with details
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            details = {}

            # Description
            desc = soup.find('div', class_='product-description')
            if desc:
                details['description'] = desc.get_text(strip=True)

            # How to use
            how_to = soup.find('div', class_='how-to-use')
            if how_to:
                details['how_to_use'] = how_to.get_text(strip=True)

            # Ingredients
            ingredients = soup.find('div', class_='ingredients')
            if ingredients:
                ing_text = ingredients.get_text(strip=True)
                details['ingredients'] = ing_text

                # Parse into list
                if ':' in ing_text:
                    ing_text = ing_text.split(':', 1)[1]
                    details['ingredients_list'] = [
                        i.strip() for i in ing_text.split(',')
                    ]

            # Skin types
            skin_types = []
            skin_section = soup.find('div', {'data-attribute': 'skinType'})
            if skin_section:
                skin_types = [
                    item.get_text(strip=True)
                    for item in skin_section.find_all('li')
                ]
            details['skin_types'] = skin_types

            # Skin concerns
            concerns = []
            concern_section = soup.find('div', {'data-attribute': 'concern'})
            if concern_section:
                concerns = [
                    item.get_text(strip=True)
                    for item in concern_section.find_all('li')
                ]
            details['skin_concerns'] = concerns

            # Size
            size = soup.find('span', class_='product-size')
            if size:
                details['size'] = size.get_text(strip=True)

            time.sleep(1)
            return details

        except Exception as e:
            print(f"Error getting details: {e}")
            return None

