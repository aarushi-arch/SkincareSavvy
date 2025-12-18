import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def migrate_categories():
    print("Migrating categories...")
    
    mapping = {
        "cleansers": "Cleanser",
        "moisturizers": "Moisturizer",
        "exfoliants": "Exfoliant",
        "serums": "Serum",
        "toners": "Toner",
        "sunscreens": "Sunscreen",
        "eye-creams": "Eye Cream",
        "masks": "Mask",
    }
    
    total_updated = 0
    
    for old_cat, new_cat in mapping.items():
        count = Product.objects.filter(category=old_cat).update(category=new_cat)
        if count > 0:
            print(f"Updated {count} products from '{old_cat}' to '{new_cat}'")
            total_updated += count
            
    print(f"\nTotal products updated: {total_updated}")
    
    # Verify
    print("\nNew Category Distribution:")
    categories = Product.objects.values_list('category', flat=True).distinct()
    for cat in categories:
        c = Product.objects.filter(category=cat).count()
        print(f"  '{cat}': {c}")

if __name__ == "__main__":
    migrate_categories()
