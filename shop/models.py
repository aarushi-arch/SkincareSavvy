from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    description = models.TextField()

    suitable_skin_types = models.JSONField()
    targets_concerns = models.JSONField()

    def __str__(self):
        return self.name
