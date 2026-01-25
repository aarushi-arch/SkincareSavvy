from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Cart, CartItem, Order, OrderItem
from recommendations.models import Product

class ShopHealthCheck(APIView):
    def get(self, request):
        return Response({"status": "shop app working"})

class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response(
                {"error": "Product ID required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        cart_item.save()

        return Response(
            {"message": "Product added to shelf"},
            status=status.HTTP_200_OK
        )

@login_required
def my_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    context = {
        "cart": cart,
        "items": cart.items.select_related("product"),
    }

    return render(request, "shop/my_cart.html", context)

@login_required
def remove_from_cart(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    item.delete()
    messages.success(request, f"Removed from your shelf.")
    return redirect("my_cart")

@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items.exists():
        messages.warning(request, "Your shelf is empty!")
        return redirect("my_cart")

    # Create Order
    order = Order.objects.create(
        user=request.user,
        total_amount=cart.total_price
    )

    # Transfer items to OrderItems
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price_at_order=item.product.price or 0
        )
    
    # Clear Cart
    cart_items.delete()

    messages.success(request, "Order placed successfully! 🌿")
    return redirect("order_success", order_id=order.id)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_success.html", {"order": order})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "shop/my_orders.html", {"orders": orders})
