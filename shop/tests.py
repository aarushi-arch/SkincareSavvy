from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Order, OrderItem
from recommendations.models import Product

User = get_user_model()

class CheckoutAddressShippingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'pass')
        self.client.login(username='u', password='pass')
        self.product = Product.objects.create(name='P1', price=200)
        # create a cart item via Cart model to simulate checkout
        from .models import Cart, CartItem
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)

    def test_checkout_saves_address_and_shipping(self):
        url = reverse('shop-checkout')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        payload = {
            'email': 'u@example.com',
            'phone': '9999999999',
            'address': '221B Baker Street',
            'city': 'London',
            'postal_code': 'NW1',
            'country': 'UK',
        }
        resp = self.client.post(url, payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertIn('Baker Street', order.address)
        self.assertTrue(order.shipping_charge >= 0)
        self.assertEqual(order.total_including_shipping, order.total_amount + order.shipping_charge)

    def test_my_orders_shows_address_and_shipping(self):
        # create an order with address/shipping and ensure the orders page shows them
        order = Order.objects.create(user=self.user, total_amount=100, shipping_charge=20, address='addr', city='C', postal_code='P', country='CT')
        url = reverse('my_orders')
        resp = self.client.get(url)
        self.assertContains(resp, 'addr')
        self.assertContains(resp, '₹ 20')

    @override_settings(ES_EWA_AVAILABLE=True)
    def test_checkout_shows_esewa_button_when_available(self):
        """Checkout page should show a 'Pay with eSewa' button when eSewa is enabled."""
        url = reverse('shop-checkout')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Pay with eSewa')
        self.assertContains(resp, reverse('esewa-checkout-cart'))

    def test_reorder_copies_items_into_cart_and_redirects(self):
        order = Order.objects.create(user=self.user, total_amount=500, shipping_charge=20)
        OrderItem.objects.create(order=order, product=self.product, quantity=2, price_at_order=self.product.price)

        resp = self.client.post(reverse('order-reorder', args=[order.id]), follow=True)
        self.assertEqual(resp.status_code, 200)
        from .models import Cart, CartItem
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        ci = cart.items.first()
        self.assertEqual(ci.product, self.product)
        self.assertEqual(ci.quantity, 2)
        self.assertContains(resp, 'Shipping')

    def test_checkout_item_copies_single_item_into_cart_and_redirects(self):
        order = Order.objects.create(user=self.user, total_amount=500, shipping_charge=20)
        oi = OrderItem.objects.create(order=order, product=self.product, quantity=2, price_at_order=self.product.price)

        resp = self.client.post(reverse('order-item-checkout', args=[order.id, oi.id]), follow=True)
        self.assertEqual(resp.status_code, 200)
        from .models import Cart, CartItem
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        ci = cart.items.first()
        self.assertEqual(ci.product, self.product)
        self.assertEqual(ci.quantity, 2)
        self.assertContains(resp, 'Shipping')

    def test_cannot_checkout_item_from_cancelled_order(self):
        order = Order.objects.create(user=self.user, total_amount=200, shipping_charge=0, status='Cancelled')
        oi = OrderItem.objects.create(order=order, product=self.product, quantity=1, price_at_order=self.product.price)

        resp = self.client.post(reverse('order-item-checkout', args=[order.id, oi.id]), follow=True)
        self.assertContains(resp, 'Cannot reorder a cancelled order')

    @override_settings(ES_EWA_AVAILABLE=True)
    def test_reorder_redirects_to_esewa_when_requested(self):
        order = Order.objects.create(user=self.user, total_amount=500, shipping_charge=20)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price_at_order=self.product.price)

        resp = self.client.post(reverse('order-reorder-esewa', args=[order.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('esewa-checkout-cart'))

    def test_cannot_reorder_cancelled_order(self):
        order = Order.objects.create(user=self.user, total_amount=200, shipping_charge=0, status='Cancelled')
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price_at_order=self.product.price)

        resp = self.client.post(reverse('order-reorder', args=[order.id]), follow=True)
        self.assertContains(resp, 'Cannot reorder a cancelled order')

    def test_settings_does_not_add_missing_esewa_to_installed_apps(self):
        """Ensure we never put a missing third-party 'esewa' into INSTALLED_APPS (prevents ModuleNotFoundError).

        Tests may still set ES_EWA_AVAILABLE=True to exercise templates; that should not cause Django to try to import an app
        called 'esewa' unless the package is actually installed.
        """
        import importlib.util
        from django.conf import settings as djsettings

        spec = importlib.util.find_spec('esewa')
        # if package is not installed, it must not appear in INSTALLED_APPS
        if spec is None:
            self.assertNotIn('esewa', djsettings.INSTALLED_APPS)
        else:
            # if package is present, it's allowed to be in INSTALLED_APPS
            self.assertIn('esewa', djsettings.INSTALLED_APPS)

