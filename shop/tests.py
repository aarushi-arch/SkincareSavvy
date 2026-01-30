from django.test import TestCase
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

