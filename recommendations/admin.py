from django.contrib import admin
from .models import Product, Ingredient


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'created_at']
    list_filter = ['brand', 'category', 'created_at']
    search_fields = ['name', 'brand', 'category']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'function', 'label', 'created_at']
    list_filter = ['function', 'label', 'created_at']
    search_fields = ['name', 'function']
    readonly_fields = ['created_at']
