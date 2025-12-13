"""Forms for face analysis."""
from django import forms
from .models import CNNModel


class CNNModelUploadForm(forms.ModelForm):
    """Form for uploading CNN model files."""
    
    class Meta:
        model = CNNModel
        fields = [
            'name',
            'model_type',
            'model_file',
            'training_data_file',
            'class_names_file',
            'description',
            'version',
            'accuracy',
            'base_architecture',
            'image_size',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., MobileNet Skin Types v1'
            }),
            'model_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'model_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.h5,.keras,.pb'
            }),
            'training_data_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.json'
            }),
            'class_names_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.json'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional description of the model...'
            }),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1.0'
            }),
            'accuracy': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0',
                'max': '1',
                'placeholder': '0.0000'
            }),
            'base_architecture': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., MobileNetV2, ResNet50'
            }),
            'image_size': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '224x224'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_model_file(self):
        """Validate model file."""
        model_file = self.cleaned_data.get('model_file')
        if not model_file:
            raise forms.ValidationError("Model file is required.")
        
        # Check file size (max 500MB)
        if model_file.size > 500 * 1024 * 1024:
            raise forms.ValidationError("Model file is too large. Maximum size is 500MB.")
        
        return model_file
    
    def clean_class_names_file(self):
        """Validate class names JSON file."""
        class_names_file = self.cleaned_data.get('class_names_file')
        if class_names_file:
            # Check file size (max 1MB)
            if class_names_file.size > 1024 * 1024:
                raise forms.ValidationError("Class names file is too large. Maximum size is 1MB.")
            
            # Try to parse JSON
            try:
                import json
                class_names_file.seek(0)
                json.load(class_names_file)
                class_names_file.seek(0)
            except json.JSONDecodeError:
                raise forms.ValidationError("Class names file must be valid JSON.")
        
        return class_names_file
    
    def clean_training_data_file(self):
        """Validate training data JSON file."""
        training_data_file = self.cleaned_data.get('training_data_file')
        if training_data_file:
            # Check file size (max 5MB)
            if training_data_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Training data file is too large. Maximum size is 5MB.")
            
            # Try to parse JSON
            try:
                import json
                training_data_file.seek(0)
                json.load(training_data_file)
                training_data_file.seek(0)
            except json.JSONDecodeError:
                raise forms.ValidationError("Training data file must be valid JSON.")
        
        return training_data_file

