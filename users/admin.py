from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, ShelfItem, Notification

# Unregister the default User admin if it's already registered
try:
    admin.site.unregister(User)
except admin.site.NotRegistered:
    pass

class UserAdmin(BaseUserAdmin):
    """Custom User admin to display username instead of password."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = BaseUserAdmin.list_filter + ('is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'location', 'birth_date')
    search_fields = ('user__username', 'bio', 'location')
    
class ShelfItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added_at')
    list_filter = ('added_at', 'user')
    search_fields = ('user__username', 'product__name')

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

# Register all models
admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(ShelfItem, ShelfItemAdmin)
admin.site.register(Notification, NotificationAdmin)
