import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def check_categories():
    categories = Product.objects.values_list('category', flat=True).distinct()
    print("Current Categories in DB:")
    for cat in categories:
        count = Product.objects.filter(category=cat).count()
        print(f"  '{cat}': {count} products")

if __name__ == "__main__":
    check_categories()
