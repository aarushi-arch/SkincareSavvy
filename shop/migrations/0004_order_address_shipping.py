# Generated manually: add address + shipping fields to Order
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_order_orderitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_charge",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name="order",
            name="address",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="city",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="postal_code",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="country",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
