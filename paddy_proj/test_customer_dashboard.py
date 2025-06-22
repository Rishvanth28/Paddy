#!/usr/bin/env python
import os  
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddy_proj.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from paddy_app.views import customer_dashboard
from paddy_app.models import CustomerTable

print("=== Testing Customer Dashboard View ===")

# Create a test request
factory = RequestFactory()
request = factory.get('/customer-dashboard/')

# Add session middleware  
middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

# Set up session as if customer is logged in
request.session['user_id'] = 'C1000001'  # Customer with orders
request.session['role'] = 'customer'

print(f"Session user_id: {request.session.get('user_id')}")
print(f"Session role: {request.session.get('role')}")

# Test the view (but we can't actually call it because of @role_required decorator)
# Instead, let's test the logic manually

customer_id = request.session.get('user_id')
if customer_id:
    try:
        customer = CustomerTable.objects.get(customer_id=customer_id)
        print(f"Found customer: {customer.first_name} {customer.last_name}")
        
        # Test the dashboard logic
        from paddy_app.models import Orders
        from django.db.models import Sum, Count
        
        customer_orders = Orders.objects.filter(customer=customer)
        active_orders = customer_orders  # All orders are considered active
        
        total_orders = active_orders.count()
        total_amount = active_orders.aggregate(Sum('overall_amount'))['overall_amount__sum'] or 0
        paid_amount = active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
        
        print(f"Dashboard data would show:")
        print(f"  Total orders: {total_orders}")
        print(f"  Total amount: {total_amount}")
        print(f"  Paid amount: {paid_amount}")
        print(f"  Due amount: {total_amount - paid_amount}")
        
        if total_orders > 0:
            print("✅ Customer dashboard should now display data!")
        else:
            print("❌ No orders found for this customer")
            
    except CustomerTable.DoesNotExist:
        print("❌ Customer not found")
else:
    print("❌ No customer_id in session")
