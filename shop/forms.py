from django import forms


class CheckoutForm(forms.Form):
    """Form for checkout process."""
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    city = forms.CharField(max_length=100, required=True)
    postal_code = forms.CharField(max_length=20, required=True)
    country = forms.CharField(max_length=100, required=True)


class CartItemForm(forms.Form):
    """Form for updating cart item quantity."""
    quantity = forms.IntegerField(min_value=1, max_value=999)
