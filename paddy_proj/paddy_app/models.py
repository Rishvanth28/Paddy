import re
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.db import models

def validate_gst(value):
    """ Validate GST format (15-character alphanumeric) """
    gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$')
    if value and not gst_pattern.match(value):
        raise ValidationError("Invalid GST number format.")

class AdminTable(models.Model):
    admin_id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)  # Supports `+` and leading 0s
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    user_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        """ Hash the password before saving if it's not already hashed """
        if not self.password.startswith('pbkdf2_sha256$'):  # Avoid double hashing
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        """ Verify the password using Django's check_password """
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Admin)"

class CustomerTable(models.Model):
    customer_id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    admin = models.ForeignKey(AdminTable, to_field="admin_id", on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    GST = models.CharField(max_length=15, null=True, blank=True, validators=[validate_gst])  # GST Validation added

    def save(self, *args, **kwargs):
        """ Hash the password before saving if it's not already hashed """
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        """ Verify the password using Django's check_password """
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company_name}"


class Orders(models.Model):
    order_id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey(CustomerTable, on_delete=models.CASCADE)
    admin = models.ForeignKey(AdminTable, on_delete=models.CASCADE)
    payment_status = models.IntegerField()
    overall_amount = models.BigIntegerField()
    paid_amount = models.BigIntegerField()
    product_category_id = models.IntegerField()
    quantity = models.IntegerField()
    GST = models.CharField(max_length=50, null=True, blank=True)
    lorry_number = models.CharField(max_length=50)
    driver_name = models.CharField(max_length=255)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_status = models.IntegerField()
    driver_ph_no = models.BigIntegerField()
    order_date = models.DateField()

    def __str__(self):
        return f"Order {self.order_id} - Customer: {self.customer.first_name} {self.customer.last_name}"

class Payments(models.Model):
    payment_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Orders, on_delete=models.CASCADE)
    amount = models.BigIntegerField()
    date = models.DateField()
    reference = models.CharField(max_length=255)
    proof_link = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=255)

    def __str__(self):
        return f"Payment {self.payment_id} - Order {self.order.order_id} - Amount: {self.amount}"

class Subscription(models.Model):
    sid = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(CustomerTable, on_delete=models.CASCADE)
    admin = models.ForeignKey(AdminTable, on_delete=models.CASCADE)
    payment_status = models.IntegerField()
    payment_amount = models.BigIntegerField()
    subscription_type = models.CharField(max_length=255)
    date_approved = models.DateField()
    additional_users = models.IntegerField()

    def __str__(self):
        return f"Subscription {self.sid} - {self.subscription_type} for {self.user.first_name}"
