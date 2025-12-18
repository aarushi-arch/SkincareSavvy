from django.contrib import admin
from .models import Product, Ingredient

admin.site.register(Product)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'price', 'rating', 'created_at']
    list_filter = ['brand', 'category', 'created_at']
    search_fields = ['name', 'brand', 'category', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('brand', 'name', 'category', 'product_id')
        }),
        ('URLs', {
            'fields': ('product_url', 'inci_decoder_url', 'image_url')
        }),
        ('Pricing & Reviews', {
            'fields': ('price', 'rating', 'review_count')
        }),
        ('Product Details', {
            'fields': ('description', 'how_to_use', 'size')
        }),
        ('Ingredients & Compatibility', {
            'fields': ('ingredients_json', 'skin_types', 'skin_concerns')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'function', 'label', 'created_at']
    list_filter = ['function', 'label', 'created_at']
    search_fields = ['name', 'function']
    readonly_fields = ['created_at']
