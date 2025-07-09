from django.contrib import admin
from .models import *

class AdminTableAdmin(admin.ModelAdmin):
    list_display = ("admin_id", "phone_number", "email", "first_name", "last_name")  # Show in list
    readonly_fields = ("admin_id",)  # Make primary key read-only in form
    ordering = ("admin_id",)  # Order by primary key

class CustomerTableAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "phone_number", "email", "first_name", "last_name")  # Show in list
    readonly_fields = ("customer_id",)  # Make primary key read-only in form
    ordering = ("customer_id",)


for model in [AdminTable, CustomerTable, Orders, Payments, Subscription,UserIncreaseSubscription,OrderItems,CashPaymentRequest]:
    if model not in admin.site._registry:
        admin.site.register(model)

