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

admin.site.register(AdminTable, AdminTableAdmin)
admin.site.register(CustomerTable, CustomerTableAdmin)

admin.site.register(Payments)
admin.site.register(Subscription)

