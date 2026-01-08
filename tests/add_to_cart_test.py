import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

from recommendations.models import Product
from shop.models import Cart, CartItem

User = get_user_model()

# Create test user
username = "test_shelf_user"
password = "testpassword123"

user, created = User.objects.get_or_create(username=username)
if created:
    user.set_password(password)
    user.save()

# Create test product
product, _ = Product.objects.get_or_create(
    name="Test Product",
    defaults={"price": 0.0}
)

client = Client()
client.force_login(user)

# Call add-to-cart API
response = client.post(
    "/shop/add-to-cart/",
    json.dumps({"product_id": product.id}),
    content_type="application/json"
)

print("status_code:", response.status_code)
print("content:", response.json())

# Verify cart item created
cart = Cart.objects.get(user=user)
items_count = CartItem.objects.filter(cart=cart, product=product).count()
print("cart_item_count:", items_count)

# Test unauthenticated request
client.logout()
response2 = client.post(
    "/shop/add-to-cart/",
    json.dumps({"product_id": product.id}),
    content_type="application/json"
)

print("unauth_status:", response2.status_code)
