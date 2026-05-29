from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm
from recommendations.models import Product
from users.models import Notification  # noqa: F401 – used by signals.py indirectly
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

# eSewa integration (manual implementation)
import uuid
import time
import hashlib
import hmac
import base64

# PayPal integration (built-in urllib, no extra package)
import urllib.request
import urllib.parse


def generate_esewa_signature(total_amount, transaction_uuid, product_code, secret_key):
    """Generate HMAC SHA256 signature for eSewa payment"""
    # Create the message to sign
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    
    # Generate HMAC SHA256 hash
    secret = secret_key.encode('utf-8')
    msg = message.encode('utf-8')
    signature = hmac.new(secret, msg, hashlib.sha256).digest()
    
    # Encode to base64
    return base64.b64encode(signature).decode('utf-8')


def generate_esewa_form(amount, tax_amount, total_amount, transaction_uuid, product_code, success_url, failure_url, secret_key, product_name="Product"):
    """Generate eSewa payment form HTML"""
    
    # Generate signature
    signature = generate_esewa_signature(total_amount, transaction_uuid, product_code, secret_key)
    
    # Get eSewa URL (test or production)
    esewa_url = getattr(settings, 'ESEWA_URL', 'https://rc-epay.esewa.com.np/api/epay/main/v2/form')
    
    # Generate form HTML
    form_html = f'''
    <form id="esewaForm" action="{esewa_url}" method="POST">
        <input type="hidden" name="amount" value="{amount}">
        <input type="hidden" name="tax_amount" value="{tax_amount}">
        <input type="hidden" name="total_amount" value="{total_amount}">
        <input type="hidden" name="transaction_uuid" value="{transaction_uuid}">
        <input type="hidden" name="product_code" value="{product_code}">
        <input type="hidden" name="product_service_charge" value="0">
        <input type="hidden" name="product_delivery_charge" value="0">
        <input type="hidden" name="success_url" value="{success_url}">
        <input type="hidden" name="failure_url" value="{failure_url}">
        <input type="hidden" name="signed_field_names" value="total_amount,transaction_uuid,product_code">
        <input type="hidden" name="signature" value="{signature}">
        <button type="submit" class="btn btn-primary">Pay with eSewa</button>
    </form>
    '''
    
    return form_html



# ---------------------------------------------------------------------------
# PayPal helpers
# ---------------------------------------------------------------------------

def _paypal_base_url():
    sandbox = getattr(settings, 'PAYPAL_SANDBOX', True)
    return 'https://api-m.sandbox.paypal.com' if sandbox else 'https://api-m.paypal.com'


def _paypal_get_access_token():
    """Exchange client credentials for a PayPal Bearer token."""
    client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
    secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
    base = _paypal_base_url()

    credentials = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()

    req = urllib.request.Request(
        f"{base}/v1/oauth2/token",
        data=data,
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())['access_token']


@login_required
@csrf_exempt
def paypal_create_order(request):
    """
    Called by the PayPal JS SDK (via fetch POST) to create a PayPal Order.
    Can handle either the full cart or a single product (if product_id is in POST body).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body) if request.body else {}
    except Exception:
        body = {}

    product_id = body.get('product_id')
    amount_npr = Decimal('0')
    description = "SkincareSavvy Order"

    if product_id:
        product = get_object_or_404(Product, id=product_id)
        amount_npr = product.price or Decimal('0')
        description = f"Buy Now: {product.name}"
    else:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        if not cart.items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        
        # Compute total with shipping
        free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
        shipping_rate  = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
        shipping = Decimal('0') if cart.total_price >= free_threshold else shipping_rate
        amount_npr = cart.total_price + shipping
        description = "Cart Checkout"

    # Convert to USD
    NPR_TO_USD = Decimal('133.00')
    total_usd = round(float(amount_npr / NPR_TO_USD), 2)

    try:
        token = _paypal_get_access_token()
        base  = _paypal_base_url()

        payload = json.dumps({
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(total_usd),
                },
                "description": description,
            }],
        }).encode()

        req = urllib.request.Request(
            f"{base}/v2/checkout/orders",
            data=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req) as resp:
            order_data = json.loads(resp.read())

        # Store details for capture verification
        request.session['paypal_transaction'] = {
            'paypal_order_id': order_data['id'],
            'product_id': product_id, # None if cart checkout
            'total_npr': str(amount_npr),
        }
        return JsonResponse({'id': order_data['id']})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@csrf_exempt
def paypal_capture_order(request):
    """
    Called by the JS SDK after the buyer approves the payment.
    Captures the PayPal order, then creates the Django Order.
    Returns JSON: { "status": "success", "order_id": <django_order_id> }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    paypal_order_id = body.get('paypal_order_id')
    stored = request.session.get('paypal_transaction', {})

    if not paypal_order_id or paypal_order_id != stored.get('paypal_order_id'):
        return JsonResponse({'error': 'Order ID mismatch or session expired'}, status=400)

    try:
        token = _paypal_get_access_token()
        base  = _paypal_base_url()

        # Capture the approved PayPal order
        req = urllib.request.Request(
            f"{base}/v2/checkout/orders/{paypal_order_id}/capture",
            data=b'{}',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req) as resp:
            capture_data = json.loads(resp.read())

        if capture_data.get('status') != 'COMPLETED':
            return JsonResponse({'error': 'Payment not completed'}, status=400)

        # Create the Django Order
        product_id = stored.get('product_id')
        
        if product_id:
            # Single product checkout
            product = get_object_or_404(Product, id=product_id)
            order = Order.objects.create(
                user=request.user,
                total_amount=product.price or 0,
                shipping_charge=0, # Buy Now assumes direct pickup or free shipping for simplicity here
                payment_method='PayPal',
                transaction_id=paypal_order_id,
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                price_at_order=product.price or 0,
            )
        else:
            # Cart checkout
            cart = get_object_or_404(Cart, user=request.user)
            free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
            shipping_rate  = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
            shipping = Decimal('0') if cart.total_price >= free_threshold else shipping_rate

            order = Order.objects.create(
                user=request.user,
                total_amount=cart.total_price,
                shipping_charge=shipping,
                payment_method='PayPal',
                transaction_id=paypal_order_id,
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_order=item.product.price or 0,
                )
            cart.items.all().delete()

        request.session.pop('paypal_transaction', None)
        messages.success(request, f"PayPal payment successful! Order #{order.id} placed. ")
        return JsonResponse({'status': 'success', 'order_id': order.id})

    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


# ---------------------------------------------------------------------------
# eSewa views
# ---------------------------------------------------------------------------

@login_required
def esewa_checkout(request, product_id):
    """Start an eSewa checkout for a single product (product-level "Buy now")."""
    product = get_object_or_404(Product, id=product_id)
    transaction_uuid = f"{uuid.uuid4()}-{int(time.time() * 1000)}"
    
    # Get eSewa configuration from settings
    product_code = getattr(settings, 'ESEWA_MERCHANT_ID', 'EPAYTEST')
    secret_key = getattr(settings, 'ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
    success_url = request.build_absolute_uri('/shop/esewa/success/')
    failure_url = request.build_absolute_uri('/shop/esewa/failure/')
    
    # Calculate amounts
    amount = float(product.price)
    tax_amount = 0
    total_amount = amount + tax_amount
    
    # Generate form
    form_html = generate_esewa_form(
        amount=amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        transaction_uuid=transaction_uuid,
        product_code=product_code,
        success_url=success_url,
        failure_url=failure_url,
        secret_key=secret_key,
        product_name=product.name
    )

    return render(request, 'shop/esewa_checkout.html', {
        'form': form_html,
        'product': product,
    })


@login_required
def esewa_checkout_cart(request):
    """Start an eSewa checkout for the current user's cart (cart-level)."""
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if not cart.items.exists():
        messages.warning(request, "Your shelf is empty — add items before paying with eSewa.")
        return redirect('my_cart')

    # Compute shipping using Decimal (same as checkout)
    free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
    shipping_rate = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
    shipping = Decimal('0') if (cart.total_price >= free_threshold) else shipping_rate

    total_amount_decimal = cart.total_price + shipping
    transaction_uuid = f"{uuid.uuid4()}-{int(time.time() * 1000)}"
    
    # Get eSewa configuration from settings
    product_code = getattr(settings, 'ESEWA_MERCHANT_ID', 'EPAYTEST')
    secret_key = getattr(settings, 'ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
    success_url = request.build_absolute_uri('/shop/esewa/success/')
    failure_url = request.build_absolute_uri('/shop/esewa/failure/')
    
    # Convert to float for eSewa
    amount = float(cart.total_price)
    tax_amount = 0
    total_amount = float(total_amount_decimal)
    
    # Store transaction details in session for verification later
    request.session['esewa_transaction'] = {
        'uuid': transaction_uuid,
        'amount': str(total_amount_decimal),
        'cart_id': cart.id,
    }
    
    # Generate form
    form_html = generate_esewa_form(
        amount=amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        transaction_uuid=transaction_uuid,
        product_code=product_code,
        success_url=success_url,
        failure_url=failure_url,
        secret_key=secret_key,
        product_name="Cart Checkout"
    )

    return render(request, 'shop/esewa_checkout.html', {
        'form': form_html,
        'cart': cart,
    })


@csrf_exempt
def esewa_success(request):
    """
    eSewa redirects here (GET) after a successful payment.
    Verifies the transaction UUID stored in the session before creating an order.
    The post_save signal (signals.py) handles the notification — no manual
    Notification.objects.create() needed here.
    """
    # eSewa v2 sends a GET redirect with transaction_uuid in query params
    transaction_uuid = request.GET.get('transaction_uuid')

    # Get stored transaction from session
    stored_transaction = request.session.get('esewa_transaction', {})

    if transaction_uuid and transaction_uuid == stored_transaction.get('uuid'):
        # Transaction matches — create order
        if request.user.is_authenticated:
            cart = get_object_or_404(Cart, user=request.user)

            # Compute shipping
            free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
            shipping_rate = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
            shipping = Decimal('0') if (cart.total_price >= free_threshold) else shipping_rate

            # Create order (post_save signal fires the notification automatically)
            order = Order.objects.create(
                user=request.user,
                total_amount=cart.total_price,
                shipping_charge=shipping,
                payment_method='eSewa',
                transaction_id=transaction_uuid,
            )

            # Transfer cart items to order
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_order=item.product.price or 0,
                )

            # Clear cart and session
            cart.items.all().delete()
            request.session.pop('esewa_transaction', None)

            messages.success(request, "Payment successful! Your order has been placed. ")
            return redirect('order_success', order_id=order.id)

    # UUID mismatch or session expired — still show a neutral success message
    messages.success(request, "Payment successful! Check your orders for details.")
    return redirect('my_orders')


@csrf_exempt
def esewa_failure(request):
    """
    eSewa will redirect here if the payment failed.
    """
    # Clear session transaction data
    if 'esewa_transaction' in request.session:
        del request.session['esewa_transaction']
    
    messages.error(request, "Payment failed or was cancelled. Please try again.")
    return redirect('my_cart')


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

    # compute shipping: simple rule (free over threshold, else shipping_rate)
    from django.conf import settings
    free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
    shipping_rate = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
    shipping = Decimal('0') if (cart.total_price >= free_threshold) else shipping_rate

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
            price_at_order=item.product.price or 0,
        )

    cart_items.delete()
    messages.success(request, "Order placed successfully! 🌿")
    
    return redirect("order_success", order_id=order.id)


@login_required
def checkout(request):
    """Full checkout page with shipping info form (address, city, etc).

    On POST, validate and create an order with shipping charges. Prefills
    the user's email and shows a preview of the cart + shipping.
    """
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # compute shipping (use Decimal for arithmetic with Decimal fields)
            from django.conf import settings
            free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
            shipping_rate = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
            shipping = Decimal('0') if (cart.total_price >= free_threshold) else shipping_rate

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
        # prefill form where possible (friendly UX)
        initial = {}
        if request.user.is_authenticated:
            initial['email'] = getattr(request.user, 'email', '')
        form = CheckoutForm(initial=initial)

    # preview shipping on the checkout page (ensure Decimal arithmetic)
    from django.conf import settings
    free_threshold = Decimal(str(getattr(settings, 'SHOP_FREE_SHIPPING_THRESHOLD', 1000)))
    shipping_rate = Decimal(str(getattr(settings, 'SHOP_SHIPPING_RATE', '49.00')))
    shipping_preview = Decimal('0') if (cart.total_price >= free_threshold) else shipping_rate

    return render(request, 'shop/checkout.html', {
        'form': form,
        'cart': cart,
        'shipping_preview': shipping_preview,
        'total_with_shipping': cart.total_price + shipping_preview,
        'esewa_available': True,  # eSewa is now available with manual implementation
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
    
    Also displays shelf items (products added to shelf) at the top of the list.
    """
    # Try to load orders normally. If the DB schema hasn't been migrated
    # (missing column), catch the OperationalError and render a helpful
    # migration-required message instead of raising a 500.
    from django.db.utils import OperationalError
    from users.models import ShelfItem

    migration_needed = False
    orders = []
    shelf_items = []
    selected_order = None
    timeline_steps = ['Placed', 'Processing', 'Shipped', 'Delivered']
    selected_step_index = 0

    try:
        # Get shelf items (most recent first)
        shelf_items = (
            ShelfItem.objects
            .filter(user=request.user)
            .select_related('product')
            .order_by('-added_at')
        )
        
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
        shelf_items = []
        selected_order = None
        # log for debugging (keeps behavior similar to previous errors)
        import logging
        logging.getLogger(__name__).warning("Orders fetch failed: %s", exc)

    # eSewa is now available with manual implementation
    esewa_available = True
    paypal_client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')

    return render(
        request,
        "shop/my_orders.html",
        {
            "orders": orders,
            "shelf_items": shelf_items,
            "selected_order": selected_order,
            "timeline_steps": timeline_steps,
            "selected_step_index": selected_step_index,
            "migration_needed": migration_needed,
            "esewa_available": esewa_available,
            "paypal_client_id": paypal_client_id,
        },
    )


@login_required
def reorder_to_cart(request, order_id):
    """Copy an existing order's items into the user's cart and redirect to checkout.

    - POST-only for safety
    - clears existing cart items (user expectation: reorder replaces cart)
    - disallows re-ordering cancelled orders
    """
    if request.method != 'POST':
        return redirect('order-detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Cancelled':
        messages.warning(request, "Cannot reorder a cancelled order.")
        return redirect('my_orders')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart.items.all().delete()

    for oi in order.items.all():
        CartItem.objects.create(cart=cart, product=oi.product, quantity=oi.quantity)

    messages.success(request, "Added items from Order #{} to your cart.".format(order.id))
    return redirect('shop-checkout')


@login_required
def checkout_order_item(request, order_id, item_id):
    """Copy a single OrderItem into the user's cart and redirect to the checkout page.

    - POST-only for safety
    - preserves the original item's quantity
    - denies operation for cancelled orders
    """
    if request.method != 'POST':
        return redirect('order-detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Cancelled':
        messages.warning(request, "Cannot reorder a cancelled order.")
        return redirect('my_orders')

    oi = get_object_or_404(OrderItem, id=item_id, order=order)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    # replace existing cart contents (user expectation: checkout this item now)
    cart.items.all().delete()
    CartItem.objects.create(cart=cart, product=oi.product, quantity=oi.quantity)

    messages.success(request, "Added '{}' to your cart. Proceed to checkout.".format(oi.product.name))
    return redirect('shop-checkout')


@login_required
def reorder_to_esewa(request, order_id):
    """Copy order items into cart and redirect to cart-level eSewa checkout.

    Uses the same safety checks as `reorder_to_cart` but redirects to
    the eSewa cart checkout URL so the user can pay immediately.
    """
    if request.method != 'POST':
        return redirect('order-detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Cancelled':
        messages.warning(request, "Cannot reorder a cancelled order.")
        return redirect('my_orders')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart.items.all().delete()

    for oi in order.items.all():
        CartItem.objects.create(cart=cart, product=oi.product, quantity=oi.quantity)

    messages.success(request, "Proceeding to payment for Order #{}".format(order.id))
    return redirect('esewa-checkout-cart')


@login_required
def order_detail(request, order_id):
    """Show a single order's full detail (kept for template compatibility).

    Many templates previously used the name `order-detail` — provide a
    simple view so those reverse() calls keep working.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})