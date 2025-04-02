from django.db import models

class AdminTable(models.Model):
    id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.BigIntegerField()
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    user_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Admin)"

class CustomerTable(models.Model):
    id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.BigIntegerField()
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    admin = models.ForeignKey(AdminTable, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    GST = models.CharField(max_length=50, null=True, blank=True)

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
