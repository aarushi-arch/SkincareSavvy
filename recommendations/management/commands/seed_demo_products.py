from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from recommendations.models import Product


SAMPLE_PRODUCTS = [
    {
        "brand": "GlowySkin",
        "name": "Hydra Boost Serum",
        "product_url": "https://example.local/products/hydra-boost-serum",
        "price": Decimal("19.99"),
        "image_url": "https://placehold.co/400x400?text=Hydra+Boost",
        "category": "serum",
    },
    {
        "brand": "Calm & Clear",
        "name": "Gentle Cleanse Foam",
        "product_url": "https://example.local/products/gentle-cleanse-foam",
        "price": Decimal("9.99"),
        "image_url": "https://placehold.co/400x400?text=Cleanse",
        "category": "cleanser",
    },
    {
        "brand": "BarrierCare",
        "name": "Repair Moisturiser 50ml",
        "product_url": "https://example.local/products/repair-moisturiser-50ml",
        "price": Decimal("24.50"),
        "image_url": "https://placehold.co/400x400?text=Moisturiser",
        "category": "moisturizer",
    },
    {
        "brand": "SPFwise",
        "name": "Everyday Sunscreen SPF 50",
        "product_url": "https://example.local/products/everyday-spf50",
        "price": Decimal("14.00"),
        "image_url": "https://placehold.co/400x400?text=SPF50",
        "category": "sunscreen",
    },
    {
        "brand": "BrightLab",
        "name": "Vitamin C Glow",
        "product_url": "https://example.local/products/vitc-glow",
        "price": Decimal("29.00"),
        "image_url": "https://placehold.co/400x400?text=Vitamin+C",
        "category": "treatment",
    },
]


class Command(BaseCommand):
    help = "Create a small set of demo products for local development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate demo products (delete + create)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options.get("force")
        created = 0
        if force:
            # remove any sample products that match our example URLs
            urls = [p["product_url"] for p in SAMPLE_PRODUCTS]
            Product.objects.filter(product_url__in=urls).delete()

        for data in SAMPLE_PRODUCTS:
            obj, was_created = Product.objects.get_or_create(
                product_url=data["product_url"],
                defaults={
                    "brand": data.get("brand", ""),
                    "name": data.get("name", ""),
                    "price": data.get("price"),
                    "image_url": data.get("image_url", ""),
                    "category": data.get("category", ""),
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Demo products ensured (created={created})"))
