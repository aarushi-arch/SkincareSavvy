from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import CNNModel, YOLOModel


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
            'fields': ('model_file', 'training_data_file', 'class_names_file'),
            'description': 'For skin concerns models, class_names_file is required.'
        }),
        ('Model Details', {
            'fields': ('base_architecture', 'image_size', 'accuracy', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def clean(self):
        """Validate that skin concerns models have class names file."""
        super().clean()
        if self.model_type == 'skin_concerns' and not self.class_names_file:
            raise ValidationError(
                'Skin concerns models require a class_names_file to be uploaded.'
            )
    
    def save_model(self, request, obj, form, change):
        """Override save to validate before saving."""
        try:
            self.clean()
        except ValidationError as e:
            raise ValidationError(e.message)
        super().save_model(request, obj, form, change)
        
        # Log the action
        if obj.is_active:
            print(f"✓ Activated {obj.model_type} model: {obj.name}")
        else:
            print(f"✓ Deactivated {obj.name}")


@admin.register(YOLOModel)
class YOLOModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
