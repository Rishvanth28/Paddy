#!/usr/bin/env python
import os
import sys
import django
import json

# Add the project directory to Python path  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddy_proj.settings')
django.setup()

from paddy_app.models import CustomerTable, Orders
from django.db.models import Sum, Count
from datetime import datetime, timedelta

print("=== Testing Customer Dashboard Context Data ===")

# Test with customer C1000001 (has orders)
customer = CustomerTable.objects.get(customer_id='C1000001')
print(f"Testing with customer: {customer.customer_id} - {customer.first_name} {customer.last_name}")

# Calculate date ranges
today = datetime.now().date()
current_year = today.year

# Get orders data for this customer
customer_orders = Orders.objects.filter(customer=customer)
active_orders = customer_orders  # All orders are considered active

# Basic order statistics
total_orders = active_orders.count()
total_amount = active_orders.aggregate(Sum('overall_amount'))['overall_amount__sum'] or 0
paid_amount = active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0

# Order categories data for pie chart
category_data = []
categories = active_orders.values('category').annotate(count=Count('category')).order_by('-count')
for category in categories:
    if category['category']:  # Ensure category is not None
        category_data.append({
            'name': category['category'],
            'count': category['count']
        })

print(f"Category data: {category_data}")

# Monthly orders data for line chart
monthly_orders = []
monthly_revenue = []

# Get orders for current year grouped by month
for month in range(1, 13):
    month_orders = active_orders.filter(
        order_date__year=current_year,
        order_date__month=month
    )
    order_count = month_orders.count()
    revenue = month_orders.aggregate(Sum('overall_amount'))['overall_amount__sum'] or 0
    
    monthly_orders.append(order_count)
    monthly_revenue.append(float(revenue))

print(f"Monthly orders: {monthly_orders}")
print(f"Monthly revenue: {monthly_revenue}")

# Test JSON serialization
try:
    category_json = json.dumps(category_data)
    monthly_orders_json = json.dumps(monthly_orders)
    monthly_revenue_json = json.dumps(monthly_revenue)
    print("✅ JSON serialization successful")
    print(f"Category JSON: {category_json}")
except Exception as e:
    print(f"❌ JSON serialization failed: {e}")

print(f"\nContext data summary:")
print(f"  total_orders: {total_orders}")
print(f"  total_amount: {total_amount}")
print(f"  paid_amount: {paid_amount}")
print(f"  due_amount: {total_amount - paid_amount}")
print(f"  category_data length: {len(category_data)}")
print(f"  monthly_orders sum: {sum(monthly_orders)}")
print(f"  monthly_revenue sum: {sum(monthly_revenue)}")
