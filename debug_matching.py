
import os
import django
import pandas as pd

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product
from recommendations.recommender_engine import skincare_recommendations, get_unique_product_names

def check_matching():
    print("Fetching unique product names from recommender...")
    names = get_unique_product_names()
    if not names:
        print("No products found in recommender engine!")
        return

    first_product = names[0]
    print(f"Getting recommendations for: {first_product}")
    
    try:
        recs_df = skincare_recommendations(first_product, top_k=5)
        print("\nRecommendations from engine:")
        print(recs_df[['product_name', 'product_href', 'product_type']])
        
        rec_urls = recs_df['product_href'].tolist() if 'product_href' in recs_df.columns else []
        if not rec_urls and 'product_url' in recs_df.columns:
            rec_urls = recs_df['product_url'].tolist()
            
        print(f"\nURLs to lookup: {rec_urls}")
        
        # Check DB
        db_products = Product.objects.filter(product_url__in=rec_urls)
        print(f"\nFound {db_products.count()} matching products in DB by URL.")
        
        # Check by name
        rec_names = recs_df['product_name'].tolist()
        db_products_by_name = Product.objects.filter(name__in=rec_names)
        print(f"Found {db_products_by_name.count()} matching products in DB by Name.")
        
        # Show what is in DB
        if db_products_by_name.exists():
            print("\nSample DB Products found by name:")
            for p in db_products_by_name:
                print(f"- {p.name} | URL: {p.product_url}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_matching()
