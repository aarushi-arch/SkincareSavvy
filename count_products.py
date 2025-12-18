import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def count_products():
    count = Product.objects.count()
    print(f"Total products in database: {count}")
    
    # Breakdown by category
    categories = Product.objects.values_list('category', flat=True).distinct()
    for cat in categories:
        c_count = Product.objects.filter(category=cat).count()
        print(f"  - {cat}: {c_count}")

if __name__ == "__main__":
    count_products()
