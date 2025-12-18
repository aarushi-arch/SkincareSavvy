import os
import django
import sys
from django.core.management import call_command

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

def scrape_remaining():
    remaining_categories = [
        "serums",
        "toners",
        "sunscreens",
        "eye-creams",
        "masks"
    ]
    
    print(f"Starting batch scrape for: {', '.join(remaining_categories)}")
    
    for cat in remaining_categories:
        print(f"\n{'='*50}")
        print(f"Processing Category: {cat}")
        print(f"{'='*50}")
        try:
            call_command('scrape_paulas_choice', category=cat)
        except Exception as e:
            print(f"Error scraping {cat}: {e}")
            
    print("\nBatch scraping completed!")

if __name__ == "__main__":
    scrape_remaining()
