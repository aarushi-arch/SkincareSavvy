import os
import django
import sys
from django.db.models import Count

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def verify_all():
    total_count = Product.objects.count()
    print(f"Total Products in DB: {total_count}")
    print("-" * 30)
    
    category_counts = Product.objects.values('category').annotate(count=Count('id')).order_by('-count')
    
    for entry in category_counts:
        print(f"{entry['category']}: {entry['count']}")

if __name__ == "__main__":
    verify_all()
