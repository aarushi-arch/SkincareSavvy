"""Models for skincare products and ingredients."""
from django.db import models
import json


class Product(models.Model):
    """Skincare product model."""
    
    brand = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=500)
    category = models.CharField(max_length=200, blank=True)
    inci_decoder_url = models.URLField(unique=True, db_index=True)
    ingredients_json = models.JSONField(default=list, blank=True, help_text="List of ingredient dicts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['brand', 'name']
        indexes = [
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.brand} - {self.name}" if self.brand else self.name
    
    @property
    def ingredients(self):
        """Return ingredients as a list of dicts."""
        if isinstance(self.ingredients_json, str):
            return json.loads(self.ingredients_json)
        return self.ingredients_json or []


class Ingredient(models.Model):
    """Ingredient model for tracking individual ingredients."""
    
    name = models.CharField(max_length=300, unique=True, db_index=True)
    function = models.CharField(max_length=200, blank=True, null=True)
    label = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
