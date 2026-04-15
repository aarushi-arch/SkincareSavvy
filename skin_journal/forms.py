from django import forms
from .models import JournalEntry


SEVERITY_CHOICES = [(0, "Not present")] + [(i, str(i)) for i in range(1, 6)]


class JournalEntryForm(forms.ModelForm):
    acne_severity       = forms.ChoiceField(choices=SEVERITY_CHOICES, required=False,
                                            widget=forms.Select(attrs={"class": "form-control"}))
    dark_spots_severity = forms.ChoiceField(choices=SEVERITY_CHOICES, required=False,
                                            widget=forms.Select(attrs={"class": "form-control"}))
    wrinkles_severity   = forms.ChoiceField(choices=SEVERITY_CHOICES, required=False,
                                            widget=forms.Select(attrs={"class": "form-control"}))

    class Meta:
        model  = JournalEntry
        fields = ["date", "skin_condition",
                  "acne_severity", "dark_spots_severity", "wrinkles_severity",
                  "notes", "products_used", "image"]
        widgets = {
            "date":  forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "skin_condition": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4,
                                           "placeholder": "How did your skin feel today? Any reactions?"}),
            "products_used": forms.TextInput(attrs={"class": "form-control",
                                                    "placeholder": "e.g. Cetaphil Cleanser, Niacinamide Serum"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }
