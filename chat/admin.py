from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'admin_reply', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'message', 'admin_reply')
    readonly_fields = ('user', 'message', 'created_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Message Details', {
            'fields': ('user', 'message', 'created_at')
        }),
        ('Admin Reply', {
            'fields': ('admin_reply',),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False  # Prevent adding messages from admin
