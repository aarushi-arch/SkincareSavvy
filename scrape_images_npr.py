import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import concurrent.futures
from urllib.parse import urljoin, urlparse

# Path to the CSV file
file_path = "recommendations/notebooks/updated_products_with_images_npr.csv"

# Load your CSV
if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
    exit(1)

df = pd.read_csv(file_path)

# Make sure your column name is correct
URL_COLUMN = "product_url"
IMAGE_COLUMN = "image_url"

# Create image column if it doesn't exist
if IMAGE_COLUMN not in df.columns:
    df[IMAGE_COLUMN] = ""

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def extract_image(url):
    """
    Robust image extraction logic targeting product images.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Check Open Graph meta tag (Most reliable for product image)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return urljoin(url, og_image.get("content"))

        # 2. Check Twitter card image
        twitter_image = soup.find("meta", name="twitter:image")
        if twitter_image and twitter_image.get("content"):
            return urljoin(url, twitter_image.get("content"))

        # 3. Check itemprop image (standard Schema.org)
        itemprop_image = soup.find("img", itemprop="image")
        if itemprop_image:
            src = itemprop_image.get("src") or itemprop_image.get("data-src")
            if src:
                return urljoin(url, src)

        # 4. Final fallback: Look for images in likely containers or just pick the first one
        # For LookFantastic, product images are often high res versions
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if src and "logo" not in src.lower() and "icon" not in src.lower() and "banner" not in src.lower():
                return urljoin(url, src)

        return None

    except Exception as e:
        # print(f"Error fetching {url}: {e}")
        return None

def process_row(index, url):
    """Helper for parallel execution."""
    image = extract_image(url)
    return index, image

# Identify rows that need an image
to_process = []
for i, row in df.iterrows():
    url = row[URL_COLUMN]
    img = row[IMAGE_COLUMN]
    
    # Process if URL exists and image is missing or not a valid URL
    if pd.notna(url) and (pd.isna(img) or img == "" or not str(img).startswith("http")):
        to_process.append((i, url))

total_to_process = len(to_process)
print(f"Total products to process: {total_to_process} / {len(df)}")

if total_to_process == 0:
    print("All products already have images. Exiting.")
    exit(0)

# Use ThreadPoolExecutor for background scraping
completed = 0
updated = 0

# Limit workers to 5-10 to avoid overwhelming the site or getting blocked
workers = 10 

with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
    # Schedule the scraping tasks
    future_to_index = {executor.submit(process_row, i, url): i for i, url in to_process}
    
    for future in concurrent.futures.as_completed(future_to_index):
        index, image_url = future.result()
        completed += 1
        
        if image_url:
            df.at[index, IMAGE_COLUMN] = image_url
            updated += 1
            print(f"[{completed}/{total_to_process}] Found: {image_url}")
        else:
            print(f"[{completed}/{total_to_process}] Failed to find image for row {index}")
            
        # Periodic save every 20 completed tasks
        if completed % 20 == 0:
            df.to_csv(file_path, index=False)
            print(f"--- Saved progress ({completed} processed) ---")

# Save final result
df.to_csv(file_path, index=False)
print(f"\n✅ Scraping complete!")
print(f"Total products: {len(df)}")
print(f"Processed: {completed}")
print(f"New images found: {updated}")
