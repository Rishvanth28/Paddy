# forms.py
from django import forms

class CustomReportForm(forms.Form):
    order_id = forms.BooleanField(required=False, label="Order ID")
    admin = forms.BooleanField(required=False, label="Admin Details")
    customer = forms.BooleanField(required=False, label="Customer Details")
    order_date = forms.BooleanField(required=False, label="Order Date")
    delivery_date = forms.BooleanField(required=False, label="Delivery Date")
    product_details = forms.BooleanField(required=False, label="Product Info")
    batch_expiry = forms.BooleanField(required=False, label="Batch & Expiry")
    quantity = forms.BooleanField(required=False, label="Quantity/Unit")
    price = forms.BooleanField(required=False, label="Price")
    total = forms.BooleanField(required=False, label="Total Amount")
    payment = forms.BooleanField(required=False, label="Payment Info")
    delivery = forms.BooleanField(required=False, label="Delivery Status")
    payment_deadline = forms.BooleanField(required=False, label="Payment Deadline")
    lorry_details = forms.BooleanField(required=False, label="Lorry Details")
