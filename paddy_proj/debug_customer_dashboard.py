#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddy_proj.settings')
django.setup()

from paddy_app.models import CustomerTable, Orders
from django.db.models import Sum, Count

print("=== DEBUG: Customer Dashboard Logic Test ===")

# Test with a customer that has orders
customer = CustomerTable.objects.filter(customer_id='C1000001').first()
if customer:
    print(f"Testing with customer: {customer.customer_id} - {customer.first_name} {customer.last_name}")
    
    # Get orders data for this customer
    customer_orders = Orders.objects.filter(customer=customer)
    print(f"Total customer orders: {customer_orders.count()}")
      # Use all orders for statistics (no need to exclude completed payments)
    active_orders = customer_orders  # All orders are considered active
    print(f"Active orders (all orders): {active_orders.count()}")
    
    # Basic order statistics
    total_orders = active_orders.count()
    total_amount = active_orders.aggregate(Sum('overall_amount'))['overall_amount__sum'] or 0
    paid_amount = active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    
    print(f"Total orders: {total_orders}")
    print(f"Total amount: {total_amount}")
    print(f"Paid amount: {paid_amount}")
    
    # Delivery status counts
    pending_delivery = active_orders.filter(delivery_status=0).count()
    completed_delivery = active_orders.filter(delivery_status=1).count()
    
    print(f"Pending delivery: {pending_delivery}")
    print(f"Completed delivery: {completed_delivery}")
    
    # Payment status counts
    pending_payment = active_orders.filter(payment_status=0).count()
    completed_payment = active_orders.filter(payment_status=1).count()
    
    print(f"Pending payment: {pending_payment}")
    print(f"Completed payment: {completed_payment}")
    
    # Recent orders (last 5)
    recent_orders = active_orders.order_by('-order_date')[:5]
    print(f"Recent orders count: {recent_orders.count()}")
    
    for order in recent_orders:
        print(f"  Order {order.order_id}: {order.order_date}, Amount: {order.overall_amount}")

print("\n=== Testing with customer that has orders including cancelled ===")
customer2 = CustomerTable.objects.filter(customer_id='C1000002').first()
if customer2:
    print(f"Testing with customer: {customer2.customer_id} - {customer2.first_name} {customer2.last_name}")
    
    customer_orders = Orders.objects.filter(customer=customer2)
    print(f"Total customer orders: {customer_orders.count()}")
    
    for order in customer_orders:
        print(f"  Order {order.order_id}: Status={order.payment_status}, Delivery={order.delivery_status}, Amount={order.overall_amount}")
