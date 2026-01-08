from django.urls import path
from .views import (
    ShopHealthCheck,
    AddToCartAPIView,
    my_cart,
)

urlpatterns = [
    path("health/", ShopHealthCheck.as_view(), name="shop_health"),
    path("add-to-cart/", AddToCartAPIView.as_view(), name="add_to_cart"),
    path("my-cart/", my_cart, name="my_cart"),
]
