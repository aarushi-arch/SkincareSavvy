from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_amount", "shipping_charge", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email")
    inlines = [OrderItemInline]
    readonly_fields = ("shipping_charge",)
    fieldsets = (
        (None, {"fields": ("user", "status")}),
        ("Pricing", {"fields": ("total_amount", "shipping_charge")}),
        ("Delivery", {"fields": ("address", "city", "postal_code", "country")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
