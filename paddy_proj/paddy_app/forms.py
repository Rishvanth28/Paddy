# forms.py
from django import forms
from .models import AdminTable, CustomerTable


class CustomReportForm(forms.Form):
    selected_admins = forms.ModelMultipleChoiceField(
        queryset=AdminTable.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )
    selected_customers = forms.ModelMultipleChoiceField(
        queryset=CustomerTable.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    order_id = forms.BooleanField(required=False)
    admin = forms.BooleanField(required=False)
    customer = forms.BooleanField(required=False)
    order_date = forms.BooleanField(required=False)
    delivery_date = forms.BooleanField(required=False)
    category = forms.BooleanField(required=False)
    overall_amount = forms.BooleanField(required=False)
    paid_amount = forms.BooleanField(required=False)
    gst = forms.BooleanField(required=False)
    payment_deadline = forms.BooleanField(required=False)
    delivery = forms.BooleanField(required=False)
    lorry_details = forms.BooleanField(required=False)
    product_details = forms.BooleanField(required=False)
    batch_expiry = forms.BooleanField(required=False)
    quantity = forms.BooleanField(required=False)
    price = forms.BooleanField(required=False)
    total = forms.BooleanField(required=False)
    payment = forms.BooleanField(required=False)