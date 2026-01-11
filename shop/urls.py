from django.urls import path
from .views import (
    ShopHealthCheck,
    AddToCartAPIView,
    my_cart,
    remove_from_cart,
    place_order,
    order_success,
    my_orders,
)

urlpatterns = [
    path("health/", ShopHealthCheck.as_view(), name="shop_health"),
    path("add-to-cart/", AddToCartAPIView.as_view(), name="add_to_cart"),
    path("my-cart/", my_cart, name="my_cart"),
    path("remove/<int:item_id>/", remove_from_cart, name="remove_from_cart"),
    path("place-order/", place_order, name="place_order"),
    path("order-success/<int:order_id>/", order_success, name="order_success"),
    path("my-orders/", my_orders, name="my_orders"),
]
