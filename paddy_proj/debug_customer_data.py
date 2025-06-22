#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddy_proj.settings')
django.setup()

from paddy_app.models import CustomerTable, Orders, AdminTable

print("=== DEBUG: Customer Dashboard Data ===")

# Check if there are any customers
customers = CustomerTable.objects.all()
print(f"Total customers in database: {customers.count()}")

if customers.count() > 0:
    for customer in customers[:5]:  # Show first 5
        print(f"Customer: {customer.customer_id} - {customer.first_name} {customer.last_name}")
        
        # Check orders for this customer
        orders = Orders.objects.filter(customer=customer)
        print(f"  Orders for this customer: {orders.count()}")
        
        if orders.count() > 0:
            for order in orders[:3]:  # Show first 3 orders
                print(f"    Order {order.order_id}: Amount={order.overall_amount}, Status={order.payment_status}")
        print()

# Check admins
admins = AdminTable.objects.all()
print(f"Total admins in database: {admins.count()}")

# Check total orders
total_orders = Orders.objects.all()
print(f"Total orders in database: {total_orders.count()}")
