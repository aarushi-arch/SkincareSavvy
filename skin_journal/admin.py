from django.contrib import admin
from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display  = ["user", "date", "skin_condition", "created_at"]
    list_filter   = ["skin_condition"]
    search_fields = ["user__username", "notes"]
