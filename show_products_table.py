import os
import django
import sys
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def show_table():
    # Fetch cleansers
    products = Product.objects.filter(category='cleansers')
    
    data = []
    for p in products:
        # Parse ingredients
        # ingredients property already handles JSON parsing
        ings = p.ingredients 
        
        # Convert to comma-separated string
        if ings and isinstance(ings[0], dict):
            ing_names = [i.get('ingredient', '') for i in ings]
        else:
            ing_names = ings
            
        ing_str = ", ".join(ing_names)
        
        data.append({
            "Name": p.name,
            "Price": p.price,
            "Rating": p.rating,
            "Ingredients": ing_str
        })
    
    df = pd.DataFrame(data)
    
    # Configure pandas to show more content
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', 50) # Limit width for readability
    pd.set_option('display.width', 1000)
    
    print(f"\nFound {len(df)} products. Table View:\n")
    print(df.to_string(index=False))
    
    # Also save to CSV for them
    csv_path = "products_with_ingredients.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved full table to {csv_path}")

if __name__ == "__main__":
    show_table()
