from django.db import models
from django.contrib.auth.models import User
from recommendations.models import Product
from PIL import Image
import os


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='profile_images/default.jpg', upload_to='profile_images')
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image and hasattr(self.image, 'path') and os.path.exists(self.image.path):
            try:
                img = Image.open(self.image.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.image.path)

            except (IOError, OSError, Exception):
                # If image processing fails, just continue without resizing
                pass


class ShelfItem(models.Model):
    """Model to store products in user's shelf."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shelf_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='saved_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s saved {self.product.name}"


