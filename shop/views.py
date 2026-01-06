from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from recommendations.models import Product
from .models import Cart, CartItem, Order, OrderItem
from django.contrib import messages

def product_list(request):
    """Shop home page showing all products."""
    products = Product.objects.all()
    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)
    
    return render(request, 'shop/product_list.html', {
        'products': products,
        'selected_category': category
    })

def product_detail(request, pk):
    """Product detail page."""
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})

@login_required
def view_cart(request):
    """Display the current user's cart."""
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'shop/cart.html', {'cart': cart})

@login_required
def add_to_cart(request, product_id):
    """Add a product to the cart."""
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f"{product.name} added to cart.")
    return redirect('shop:view_cart')

@login_required
def remove_from_cart(request, item_id):
    """Remove an item from the cart."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('shop:view_cart')

@login_required
def checkout(request):
    """Handle the checkout process."""
    cart = get_object_or_404(Cart, user=request.user)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('shop:product_list')
    
    if request.method == "POST":
        # Create an Order
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_price,
            shipping_address=request.POST.get('address', 'Test Address')
        )
        
        # Move items from cart to order
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_order=item.product.price if item.product.price else 0
            )
        
        # Clear the cart
        cart.items.all().delete()
        
        messages.success(request, "Order placed successfully!")
        return render(request, 'shop/order_complete.html', {'order': order})
        
    return render(request, 'shop/checkout.html', {'cart': cart})
