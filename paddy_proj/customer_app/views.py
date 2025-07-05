from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Count, Q, Avg, Case, When, F
from django.db.models.functions import ExtractMonth, ExtractYear
from paddy_app.decorators import role_required
from paddy_app.helpers import *
from paddy_app.models import *
import json

@role_required(["customer"])
def upgrade_to_admin(request):
    customer_id = request.session.get('user_id')
    customer = CustomerTable.objects.get(customer_id=customer_id)

    # Check if already admin
    is_admin = AdminTable.objects.filter(email=customer.email).exists()
    
    if is_admin:
        messages.info(request, "You are already an admin! Access denied.")
        return render(request, 'customer_app/upgrade_to_admin.html', {'customer': customer, 'is_admin': True})

    if request.method == 'POST':
        # Create new admin
        new_admin = AdminTable(
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone_number=customer.phone_number,
            email=customer.email,
            password=customer.password,  # already hashed
            user_count=50,
        )
        new_admin.save()
        
        messages.success(request, "You have been upgraded to admin successfully!")
        return render(request, 'customer_app/upgrade_to_admin.html', {'customer': customer, 'is_admin': True})

    return render(request, 'customer_app/upgrade_to_admin.html', {'customer': customer, 'is_admin': is_admin})

@role_required(["customer"])
def customer_dashboard(request):
    from django.db.models import Sum, Count, Q, Avg, Max, F
    from datetime import datetime, timedelta
    import json
    
    # Get customer from session - using 'user_id' key as set in login
    customer_id = request.session.get('user_id')
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
    
    try:
        customer = CustomerTable.objects.get(customer_id=customer_id)
    except CustomerTable.DoesNotExist:
        messages.error(request, "Customer not found. Please log in again.")
        return redirect('login_app:login')
    
    # Calculate date ranges
    today = datetime.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    current_year = today.year
      # Get orders data for this customer
    customer_orders = Orders.objects.filter(customer=customer)
    
    # Use all orders for statistics (no need to exclude completed payments)
    active_orders = customer_orders  # All orders are considered active
    
    # Basic order statistics
    total_orders = active_orders.count()
    total_amount = active_orders.aggregate(Sum('overall_amount'))['overall_amount__sum'] or 0
    paid_amount = active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    
    # Delivery status counts
    pending_delivery = active_orders.filter(delivery_status=0).count()
    completed_delivery = active_orders.filter(delivery_status=1).count()
      # Payment status counts
    pending_payment = active_orders.filter(payment_status=0).count()
    partial_payment = active_orders.filter(payment_status=1).count()
    completed_payment = active_orders.filter(payment_status=2).count()
    
    # Recent orders (last 5)
    recent_orders = active_orders.order_by('-order_date')[:5]
    
    # Order categories data for pie chart
    category_data = []
    categories = active_orders.values('category').annotate(count=Count('category')).order_by('-count')
    for category in categories:
        if category['category']:  # Ensure category is not None
            category_data.append({
                'name': category['category'],
                'count': category['count']
            })
    
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
        monthly_revenue.append(float(revenue))      # Payment status data for doughnut chart
    payment_status_data = [
        {'name': 'Pending', 'count': pending_payment},
        {'name': 'Partial', 'count': partial_payment},
        {'name': 'Completed', 'count': completed_payment}
    ]
    
    # Filter out any status with zero count
    payment_status_data = [status for status in payment_status_data if status['count'] > 0]
    
    # Delivery status data for doughnut chart
    delivery_status_data = [
        {'name': 'Pending', 'count': pending_delivery},
        {'name': 'Completed', 'count': completed_delivery}
    ]    # Pending payments (where payment is not complete - includes unpaid and partially paid)
    pending_payments = active_orders.filter(
        Q(payment_status=0) | Q(payment_status=1)  # Unpaid or partially paid
    ).order_by('-order_date')
    
    # Calculate due amount and paid amount for each order
    for order in pending_payments:
        if order.paid_amount is None:
            order.paid_amount = 0
        order.due_amount = order.overall_amount - order.paid_amount
      # Pending deliveries (all orders that haven't been delivered yet)
    upcoming_deliveries = active_orders.filter(
        delivery_status=0  # Only pending deliveries
    ).order_by('-order_date')  # Show most recent orders first
    
    # Calculate due amount
    due_amount = total_amount - paid_amount
      # Convert data to JSON for charts
    context = {
        'customer': customer,
        'total_orders': total_orders,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'due_amount': due_amount,
        'pending_delivery': pending_delivery,
        'completed_delivery': completed_delivery,        'pending_payment': pending_payment,
        'partial_payment': partial_payment,
        'completed_payment': completed_payment,
        'recent_orders': recent_orders,        'pending_payments': pending_payments,
        'upcoming_deliveries': upcoming_deliveries,
        'category_data_json': json.dumps(category_data),
        'monthly_orders_json': json.dumps(monthly_orders),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'payment_status_json': json.dumps(payment_status_data),
        'delivery_status_json': json.dumps(delivery_status_data)
    }
    
    return render(request, 'customer_app/customer_dashboard.html', context)