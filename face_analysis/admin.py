from django.contrib import admin
from .models import CNNModel


@admin.register(CNNModel)
class CNNModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'version', 'base_architecture', 'accuracy', 'is_active', 'created_at']
    list_filter = ['model_type', 'is_active', 'base_architecture', 'created_at']
    search_fields = ['name', 'description', 'base_architecture']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'model_type', 'version', 'description')
        }),
        ('Model Files', {
            'fields': ('model_file', 'training_data_file', 'class_names_file')
        }),
        ('Model Details', {
            'fields': ('base_architecture', 'image_size', 'accuracy', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
