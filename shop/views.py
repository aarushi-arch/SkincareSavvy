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
    """Legacy endpoint: create an order from the user's cart.

    Accepts optional address fields in POST for backward compatibility.
    Prefer using `checkout` (below) for full form validation/UI.
    """
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items.exists():
        messages.warning(request, "Your shelf is empty!")
        return redirect("my_cart")

    # read optional address fields (if coming from a POST)
    address = request.POST.get('address') or None
    city = request.POST.get('city') or None
    postal_code = request.POST.get('postal_code') or None
    country = request.POST.get('country') or None

    # compute shipping: simple rule (free over ₹1000, else ₹49) — configurable via settings
    from django.conf import settings
    free_threshold = getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)
    shipping_rate = getattr(settings, 'SHOP_SHIPPING_RATE', 49.00)
    shipping = 0 if (cart.total_price >= free_threshold) else shipping_rate

    # Create Order (persist shipping + address)
    order = Order.objects.create(
        user=request.user,
        total_amount=cart.total_price,
        shipping_charge=shipping,
        address=address,
        city=city,
        postal_code=postal_code,
        country=country,
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
def checkout(request):
    """Render checkout form (uses `CheckoutForm`) and create order on POST.

    This is the canonical flow for collecting delivery address and showing
    shipping charges before creating an order.
    """
    from .forms import CheckoutForm

    cart = get_object_or_404(Cart, user=request.user)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # reuse place_order logic by POSTing the address data into it
            # (keeps a single creation path). We'll call the same helper
            # by forwarding data into place_order via the request.POST-like dict.
            # Simpler: compute shipping here and create the order directly.

            # compute shipping
            from django.conf import settings
            free_threshold = getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)
            shipping_rate = getattr(settings, 'SHOP_SHIPPING_RATE', 49.00)
            shipping = 0 if (cart.total_price >= free_threshold) else shipping_rate

            order = Order.objects.create(
                user=request.user,
                total_amount=cart.total_price,
                shipping_charge=shipping,
                address=data.get('address'),
                city=data.get('city'),
                postal_code=data.get('postal_code'),
                country=data.get('country'),
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_order=item.product.price or 0,
                )

            cart.items.all().delete()
            messages.success(request, "Order placed successfully! 🌿")
            return redirect('order_success', order_id=order.id)
    else:
        form = CheckoutForm()

    # preview shipping on the checkout page
    from django.conf import settings
    free_threshold = getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)
    shipping_rate = getattr(settings, 'SHOP_SHIPPING_RATE', 49.00)
    shipping_preview = 0 if (cart.total_price >= free_threshold) else shipping_rate

    return render(request, 'shop/checkout.html', {
        'form': form,
        'cart': cart,
        'shipping_preview': shipping_preview,
        'total_with_shipping': cart.total_price + shipping_preview,
    })

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_success.html", {"order": order})

@login_required
def my_orders(request):
    """Render user's orders as a split view (left: list, right: details).

    Supports `?order=<id>` to preselect an order. Prefetches related
    products/items to avoid N+1 queries and computes a simple
    progress index for the timeline displayed in the template.
    """
    # Try to load orders normally. If the DB schema hasn't been migrated
    # (missing column), catch the OperationalError and render a helpful
    # migration-required message instead of raising a 500.
    from django.db.utils import OperationalError

    migration_needed = False
    orders = []
    selected_order = None
    timeline_steps = ['Placed', 'Processing', 'Shipped', 'Delivered']
    selected_step_index = 0

    try:
        orders = (
            Order.objects
            .filter(user=request.user)
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

        # pick selected order from querystring (or default to first)
        selected_id = request.GET.get('order')
        if selected_id:
            try:
                selected_order = orders.get(id=selected_id)
            except Order.DoesNotExist:
                selected_order = None

        if not selected_order:
            selected_order = orders.first()

        # timeline steps & map model status to progress index
        status_progress = {
            'Pending': 0,
            'Processing': 1,
            'Shipped': 2,
            'Delivered': 3,
            'Cancelled': -1,
        }

        if selected_order and selected_order.status:
            selected_step_index = status_progress.get(selected_order.status, 0)

    except OperationalError as exc:
        # Database doesn't have the new columns yet — show a friendly banner
        # and avoid touching model fields that cause the DB to error.
        migration_needed = True
        orders = []
        selected_order = None
        # log for debugging (keeps behavior similar to previous errors)
        import logging
        logging.getLogger(__name__).warning("Orders fetch failed: %s", exc)

    return render(
        request,
        "shop/my_orders.html",
        {
            "orders": orders,
            "selected_order": selected_order,
            "timeline_steps": timeline_steps,
            "selected_step_index": selected_step_index,
            "migration_needed": migration_needed,
        },
    )


@login_required
def order_detail(request, order_id):
    """Show a single order's full detail (kept for template compatibility).

    Many templates previously used the name `order-detail` — provide a
    simple view so those reverse() calls keep working.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})
