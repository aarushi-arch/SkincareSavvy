from django.contrib import admin
from .models import Cart, CartItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'price')
    list_filter = ('brand',)
    search_fields = ('name', 'brand')
