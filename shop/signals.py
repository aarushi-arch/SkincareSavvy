from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from users.models import Notification

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """
    Automatically create a notification when a new Order is created.
    """
    if created:
        # Check if it was an eSewa or PayPal payment
        if instance.payment_method == 'eSewa':
            message = f"Payment successful! Your order #{instance.id} has been placed. 💳✨"
        elif instance.payment_method == 'PayPal':
            message = f"PayPal payment successful! Your order #{instance.id} is confirmed. 💳✅"
        else:
            message = f"Your order #{instance.id} has been placed successfully! 🌿"
        
        Notification.objects.create(
            user=instance.user,
            message=message
        )
