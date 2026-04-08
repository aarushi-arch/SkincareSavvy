"""Models for face analysis CNN models."""
import json
import os
from django.db import models
from django.core.validators import FileExtensionValidator


def yolo_model_upload_path(instance, filename):
    """Generate upload path for YOLO model files."""
    return f'face_analysis/models/yolo/{filename}'


def model_file_upload_path(instance, filename):
    """Generate upload path for model files."""
    return f'face_analysis/models/{instance.model_type}/{filename}'


def training_data_upload_path(instance, filename):
    """Generate upload path for training data files."""
    return f'face_analysis/training_data/{instance.model_type}/{filename}'


class CNNModel(models.Model):
    """Model to store uploaded CNN model files and training data."""
    
    MODEL_TYPE_CHOICES = [
        ('skin_types', 'Skin Types'),
        ('skin_concerns', 'Skin Concerns'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name for this model (e.g., 'MobileNet Skin Types v1')")
    model_type = models.CharField(
        max_length=20,
        choices=MODEL_TYPE_CHOICES,
        help_text="Type of model: skin types or skin concerns"
    )
    model_file = models.FileField(
        upload_to=model_file_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['h5', 'keras', 'pb'])],
        help_text="Upload trained model file (.h5, .keras, or .pb format)"
    )
    training_data_file = models.FileField(
        upload_to=training_data_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['json'])],
        help_text="Upload training data JSON file (class names, history, etc.)",
        blank=True,
        null=True
    )
    class_names_file = models.FileField(
        upload_to=training_data_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['json'])],
        help_text="Upload class names JSON file",
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, help_text="Optional description of the model")
    version = models.CharField(max_length=50, default='1.0', help_text="Model version")
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Model accuracy (0-1)"
    )
    base_architecture = models.CharField(
        max_length=100,
        blank=True,
        help_text="Base architecture (e.g., MobileNetV2, ResNet50)"
    )
    image_size = models.CharField(
        max_length=20,
        default='224x224',
        help_text="Input image size (e.g., '224x224')"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Set as active model for this type (only one active per type)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "CNN Model"
        verbose_name_plural = "CNN Models"
        indexes = [
            models.Index(fields=['model_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"
    
    @property
    def model_path(self):
        """Return the file system path to the model file."""
        if self.model_file:
            return self.model_file.path
        return None
    
    @property
    def class_names(self):
        """Parse and return class names from JSON file."""
        if self.class_names_file:
            try:
                with open(self.class_names_file.path, 'r') as f:
                    data = json.load(f)
                    # If it's a dict, return it as-is (the pipeline handles conversion)
                    if isinstance(data, dict):
                        return data
                    # If it's a list, return it as-is
                    if isinstance(data, list):
                        return data
                    return None
            except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
                print(f"Error reading class_names_file: {e}")
                return None
        return None
    
    @property
    def training_history(self):
        """Parse and return training history from JSON file."""
        if self.training_data_file:
            try:
                with open(self.training_data_file.path, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
        return {}
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active model per type."""
        if self.is_active:
            # Deactivate other models of the same type
            CNNModel.objects.filter(
                model_type=self.model_type,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class YOLOModel(models.Model):
    """Stores an uploaded YOLO .pt model used for acne/lesion region detection."""

    name = models.CharField(max_length=200)
    model_file = models.FileField(
        upload_to=yolo_model_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pt'])],
        help_text="Upload YOLO model weights (.pt)",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Only one YOLO model should be active at a time",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "YOLO Model"
        verbose_name_plural = "YOLO Models"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            YOLOModel.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
