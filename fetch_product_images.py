import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_product_image(product_url):
    try:
        response = requests.get(product_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        soup = BeautifulSoup(response.text, "html.parser")

        # Find image tag (this may vary depending on website)
        img_tag = soup.find("img")

        if img_tag and img_tag.get("src"):
            return img_tag["src"]

    except Exception as e:
        print(f"Error fetching image for {product_url}: {e}")

    return None

def main():
    # Load the dataset
    df = pd.read_csv('recommendations/notebooks/updated_products.csv')

    # Add image_url column if it doesn't exist
    if 'image_url' not in df.columns:
        df['image_url'] = None

    # Process first 5 products for testing
    for index, row in df.head(5).iterrows():
        product_url = row['product_url']
        if pd.isna(row.get('image_url')):  # Only fetch if not already done
            print(f"Fetching image for: {row['product_name']}")
            image_url = get_product_image(product_url)
            df.at[index, 'image_url'] = image_url
            time.sleep(1)  # Be respectful to the server

    # Save the updated dataset
    df.to_csv('recommendations/notebooks/updated_products_with_images.csv', index=False)
    print("Updated dataset saved as 'updated_products_with_images.csv'")

if __name__ == "__main__":
    main()