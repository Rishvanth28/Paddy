import re
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils.timezone import now
from datetime import timedelta

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
        """Ensure new admins get an ID >= 1000000 and hash passwords."""
        if not self.admin_id:  # Only set for new admins
            last_admin = AdminTable.objects.order_by('-admin_id').first()
            if last_admin and last_admin.admin_id >= 1000000:
                self.admin_id = last_admin.admin_id + 1
            else:
                self.admin_id = 1000000

        # Hash password if not already hashed
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)

        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        """ Verify the password using Django's check_password """
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Admin)"

class CustomerTable(models.Model):
    customer_id = models.CharField(max_length=15, primary_key=True)  # Store ID as a string (e.g., "C1000000")
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    admin = models.ForeignKey(AdminTable, to_field="admin_id", on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    GST = models.CharField(max_length=15, null=True, blank=True, validators=[validate_gst])  # GST Validation added
    address = models.TextField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        """Ensure new customers get an ID >= C1000000 and hash passwords."""
        if not self.customer_id:  # Assign new ID only for new customers
            last_customer = CustomerTable.objects.filter(customer_id__startswith="C").order_by('-customer_id').first()
            if last_customer:
                last_id = int(last_customer.customer_id[1:])  # Extract numeric part
                new_id = f"C{last_id + 1}"
            else:
                new_id = "C1000000"
            self.customer_id = new_id

        # Hash password if not already hashed
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)

        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        """ Verify the password using Django's check_password """
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Customer)"
class Orders(models.Model):
    order_id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey(CustomerTable, on_delete=models.CASCADE)
    admin = models.ForeignKey(AdminTable, on_delete=models.CASCADE)
    payment_status = models.IntegerField()
    overall_amount = models.BigIntegerField(default=0)
    paid_amount = models.BigIntegerField(null=True, blank=True)
    product_category_id = models.IntegerField()
    quantity = models.IntegerField()
    price_per_unit = models.FloatField(default=0.0)
    GST = models.CharField(max_length=50, null=True, blank=True)
    lorry_number = models.CharField(max_length=50)
    driver_name = models.CharField(max_length=255)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_status = models.IntegerField()
    driver_ph_no = models.BigIntegerField()
    order_date = models.DateField()
    payment_deadline = models.IntegerField(default=90)  # in days
    def __str__(self):
        return f"Order {self.order_id} - Customer: {self.customer.first_name} {self.customer.last_name}"

class OrderItems(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)  # Store at time of order
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    price_per_unit = models.FloatField()
    total_amount = models.FloatField()
    unit = models.CharField(max_length=50,default="Nos")  # e.g., "kg", "liters", etc.
   
    def save(self, *args, **kwargs):
        # Auto-calculate total if not provided
        if not self.total_amount:
            self.total_amount = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product_name} - {self.quantity} units for Order {self.order.order_id}"
class Payments(models.Model):
    payment_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Orders, on_delete=models.CASCADE,null=True, blank=True)
    amount = models.BigIntegerField()
    date = models.DateField()
    reference = models.CharField(max_length=255)
    proof_link = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=255)

    def __str__(self):
        return f"Payment {self.payment_id} - Order {self.order.order_id} - Amount: {self.amount}"

class Subscription(models.Model):
    sid = models.BigAutoField(primary_key=True)
    customer_id = models.ForeignKey('CustomerTable', null=True, blank=True, on_delete=models.CASCADE)
    admin_id = models.ForeignKey('AdminTable', null=True, blank=True, on_delete=models.CASCADE)
    subscription_type = models.CharField(max_length=255)  # 'admin', 'customer', etc.
    subscription_status = models.IntegerField(default=0)  # 0: Pending, 1: Active
    payment_amount = models.BigIntegerField(default=0)
    start_date = models.DateField(default=now)
    end_date = models.DateField(null=True, blank=True)
    def __str__(self):
        return f"Subscription {self.sid} - {self.subscription_type}"
    


class UserIncreaseSubscription(models.Model):
    sid = models.BigAutoField(primary_key=True)
    admin_id = models.ForeignKey('AdminTable', null=True, blank=True, on_delete=models.CASCADE)
    subscription_status = models.IntegerField(default=0)  # 0: Pending, 1: Active
    payment_amount = models.BigIntegerField(default=0)
    start_date = models.DateField(default=now)
    end_date = models.DateField(null=True, blank=True)
    additional_users = models.IntegerField(default=50)  # Number of additional users added
    def __str__(self):
        return f"Subscription {self.sid}"    