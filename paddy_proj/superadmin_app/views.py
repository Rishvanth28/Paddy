from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from .models import *
from django.db import IntegrityError
from datetime import date, timedelta
from django.core.paginator import Paginator
from django.utils import timezone
from paddy_app.decorators import *
from paddy_app.helpers import *
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db.models import Case, When, Sum, Count, F
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from paddy_app.models import *
import os
from django.db.models import Q, Prefetch
from django.db.models import Value, CharField

@role_required(["superadmin"])
def superadmin_dashboard(request):
    from django.db.models import Sum, Count, Q, Avg
    from django.db.models.functions import ExtractMonth, ExtractYear
    from datetime import datetime, timedelta
    import json
    
    # Calculate date ranges
    today = datetime.now().date()
    last_7_days = today - timedelta(days=7)
    current_month_start = today.replace(day=1)
    
    # Get all data across the platform
    all_orders = Orders.objects.all()
    all_admins = AdminTable.objects.exclude(admin_id=1000000)  # Exclude superadmin
    all_customers = CustomerTable.objects.all()
    all_payments = Payments.objects.all()
    all_subscriptions = Subscription.objects.all()
    
    # Platform-wide statistics
    total_orders = all_orders.count()
    completed_orders = all_orders.filter(delivery_status=1).count()
    pending_orders = all_orders.filter(delivery_status=0).count()
    new_orders = all_orders.filter(order_date__gte=last_7_days).count()
    
    # Admin and customer statistics
    total_admins = all_admins.count()
    total_customers = all_customers.count()
    
    # Payment statistics - only successful payments
    total_payments = all_payments.aggregate(total=Sum('amount'))['total'] or 0
    successful_payments = all_payments.filter(order__payment_status__in=[1, 2]).count()
    
    # Subscription statistics
    active_subscriptions = all_subscriptions.filter(
        subscription_status=1,
        end_date__gte=today
    ).count()
    
    expiring_subscriptions = all_subscriptions.filter(
        subscription_status=1,
        end_date__lte=today + timedelta(days=30),
        end_date__gte=today
    ).count()
    
    # Revenue statistics
    total_revenue = all_orders.filter(payment_status__in=[1, 2]).aggregate(
        total=Sum('overall_amount')
    )['total'] or 0
    
    # Average order value
    avg_order_value = all_orders.filter(payment_status__in=[1, 2]).aggregate(
        avg=Avg('overall_amount')
    )['avg'] or 0
    
    # Top product (most ordered category)
    top_product_data = all_orders.values('category').annotate(
        count=Count('category')
    ).order_by('-count').first()
    top_product = top_product_data['category'] if top_product_data and top_product_data['category'] else 'N/A'
    
    # Platform growth metrics - use created_at field for accurate counts
    new_admins_this_month = all_admins.filter(
        created_at__gte=current_month_start
    ).count() if hasattr(AdminTable, 'created_at') else 0
    
    new_customers_this_month = all_customers.filter(
        created_at__gte=current_month_start
    ).count() if hasattr(CustomerTable, 'created_at') else 0
    
    # Recent activity across platform
    recent_activity = []
    
    # Recent orders from all admins
    recent_orders = all_orders.order_by('-order_date')[:3]
    for order in recent_orders:
        recent_activity.append({
            'icon': '📦',
            'text': f'Order #{order.order_id} placed by {order.customer.first_name} {order.customer.last_name} (Admin: {order.admin.first_name})',
            'time': order.order_date.strftime('%d %b %Y')
        })
    
    # Recent payments
    recent_payments = all_payments.order_by('-date')[:2]
    for payment in recent_payments:
        recent_activity.append({
            'icon': '💰',
            'text': f'Payment ₹{payment.amount} received for Order #{payment.order.order_id if payment.order else "N/A"}',
            'time': payment.date.strftime('%d %b %Y')
        })
    
    # Recent new admins
    if hasattr(AdminTable, 'created_at'):
        recent_admins = all_admins.order_by('-created_at')[:2]
        for admin in recent_admins:
            recent_activity.append({
                'icon': '👨‍💼',
                'text': f'New admin {admin.first_name} {admin.last_name} joined the platform',
                'time': admin.created_at.strftime('%d %b %Y') if admin.created_at else 'N/A'
            })
    
    # Sort recent activity by time (simplified)
    recent_activity = sorted(
        recent_activity, 
        key=lambda x: datetime.strptime(x['time'], '%d %b %Y') if x['time'] != 'N/A' else datetime.min,
        reverse=True
    )[:5]  # Limit to 5 items
    
    # Pending subscription requests
    pending_subscription_requests = UserIncreaseSubscription.objects.filter(
        subscription_status=0
    ).count()
    
    # Chart data for analytics - similar to admin dashboard
    # Monthly orders data (last 6 months)
    monthly_orders = []
    monthly_revenue = []
    month_labels = []
    
    # Get monthly data for last 6 months
    for i in range(6):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_orders = all_orders.filter(order_date__range=[month_start, month_end]).count()
        month_revenue = all_orders.filter(
            order_date__range=[month_start, month_end],
            payment_status__in=[1, 2]
        ).aggregate(total=Sum('overall_amount'))['total'] or 0
        
        monthly_orders.insert(0, month_orders)
        monthly_revenue.insert(0, float(month_revenue))
        
        month_labels.insert(0, month_start.strftime('%b %Y'))
    
    # Category data for pie chart
    order_categories = []
    category_counts = []
    
    categories = all_orders.values('category').annotate(
        count=Count('category')
    ).order_by('-count')
    
    for cat in categories:
        if cat['category']:
            order_categories.append(cat['category'])
            category_counts.append(cat['count'])
    
    # Payment status data
    payment_completed = all_orders.filter(payment_status=2).count()
    payment_partial = all_orders.filter(payment_status=1).count()
    payment_pending = all_orders.filter(payment_status=0).count()
    
    # Admin distribution data
    admin_names = []
    admin_customer_counts = []
    
    for admin in all_admins:
        admin_names.append(f"{admin.first_name} {admin.last_name}")
        customer_count = CustomerTable.objects.filter(admin=admin).count()
        admin_customer_counts.append(customer_count)
    
    context = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'new_orders': new_orders,
        'total_admins': total_admins,
        'total_customers': total_customers,
        'total_payments': total_payments,
        'successful_payments': successful_payments,
        'active_subscriptions': active_subscriptions,
        'expiring_subscriptions': expiring_subscriptions,
        'total_revenue': total_revenue,
        'avg_order_value': round(avg_order_value, 2) if avg_order_value else 0,
        'top_product': top_product,
        'new_admins_this_month': new_admins_this_month,
        'new_customers_this_month': new_customers_this_month,
        'recent_activity': recent_activity,
        'pending_subscription_requests': pending_subscription_requests,
        # Chart data - JSON serialized for JavaScript
        'monthly_orders': json.dumps(monthly_orders),
        'monthly_revenue': json.dumps(monthly_revenue),
        'month_labels': json.dumps(month_labels),
        'order_categories': json.dumps(order_categories),
        'category_counts': json.dumps(category_counts),
        'admin_names': json.dumps(admin_names),
        'admin_customer_counts': json.dumps(admin_customer_counts),
        'payment_completed': payment_completed,
        'payment_partial': payment_partial,
        'payment_pending': payment_pending,
    }
    
    return render(request, "superadmin_app/superadmin_dashboard.html", context)

@role_required(["superadmin"])
def superadmin_subscription(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')

    # Base queryset with annotated status labels
    subscriptions_queryset = UserIncreaseSubscription.objects.annotate(
        status_label=Case(
            When(subscription_status=0, then=Value('Pending')),
            When(subscription_status=1, then=Value('Approved')),
            When(subscription_status=3, then=Value('Active')),
            default=Value('Unknown'),
            output_field=CharField()
        )
    ).order_by('-sid')

    # Apply status filter if provided
    if status_filter != '':
        subscriptions_queryset = subscriptions_queryset.filter(subscription_status=status_filter)
    
    # Pagination
    paginator = Paginator(subscriptions_queryset, 10)  # 10 items per page
    page_number = request.GET.get('page', 1)
    subscriptions = paginator.get_page(page_number)
    
    context = {
        'subscriptions': subscriptions,
    }
    
    return render(request, 'superadmin_app/superadmin_subscription.html', context)

@role_required(["superadmin"])
def superadmin_subscription_review(request):
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription_id')
        subscription_status = request.POST.get('subscription_status')
        payment_amount = request.POST.get('payment_amount')
        try:
            subscription = UserIncreaseSubscription.objects.get(sid=subscription_id)
            
            # Update subscription
            subscription.subscription_status = subscription_status
            
            if subscription_status == '1':  # If approved
                subscription.payment_amount = payment_amount
                messages.success(request, f"Subscription request #{subscription_id} has been approved.")
            elif subscription_status == '2':  # If rejected
                messages.info(request, f"Subscription request #{subscription_id} has been rejected.")
            
            subscription.save()
            
        except Exception:
            messages.error(request, "Subscription request not found.")
        
        return redirect('superadmin_app:superadmin_subscription')
    
    # If not POST, redirect to the list view
    return redirect('superadmin_app:superadmin_subscription')

@role_required(["superadmin"])
def view_admins(request):
    query = request.GET.get('q')
    admins = AdminTable.objects.exclude(admin_id=1000000)

    if query:
        admins = admins.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone_number__icontains=query)
        )

    return render(request, 'superadmin_app/view_admins.html', {'admins': admins})

@role_required(["superadmin", "admin"])
def view_customers_under_admin(request, admin_id):
    try:
        admin = AdminTable.objects.get(admin_id=admin_id)
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('superadmin_app:view_admins')

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    return render(request, 'superadmin_app/admin_customers.html', {
        'admin': admin,
        'customers': customers
    })

@role_required(["superadmin", "admin"])
def customers_under_admin(request):
    admin_id = request.session.get("user_id")  # session must store admin_id during login
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"
    if not admin_id:
        return redirect('login_app:login')  # redirect if not logged in

    # Fetch customers for the current admin
    customers = CustomerTable.objects.filter(admin_id=admin_id)

    return render(request, "superadmin_app/customers_list.html" if is_superadmin else "admin_customer_list.html", {"customers": customers})

def view_admin_subscribers(request):
    admin_subscriptions = Subscription.objects.filter(subscription_type="admin") \
                                              .select_related('admin_id') \
                                              .order_by('-start_date')
    
     # Add comparable end_date and today's date for frontend comparison
    today_date = timezone.now().date().isoformat()
    # Prepare a list with comparable end_date and today's date
    admin_subscriptions = [
        {
            "subscription": sub,
            "end_date_comparable": sub.end_date.isoformat() if sub.end_date else None,
            "today_date": today_date
        }
        for sub in admin_subscriptions
    ]
    

    return render(request, "superadmin_app/admin_subscribers.html", {
        "subscriptions": admin_subscriptions,
        "user_type": "admin",  # Make sure to pass this context
    })


def view_customer_subscribers(request):
    customer_subscriptions = Subscription.objects.filter(subscription_type="customer") \
                                                 .select_related('customer_id') \
                                                 .order_by('-start_date')

    # Add comparable end_date and today's date for frontend comparison
    today_date = timezone.now().date().isoformat()
    # Prepare a list with comparable end_date and today's date
    customer_subscriptions = [
        {
            "subscription": sub,
            "end_date_comparable": sub.end_date.isoformat() if sub.end_date else None,
            "today_date": today_date
        }
        for sub in customer_subscriptions
    ]
    
    return render(request, "superadmin_app/customer_subscribers.html", {
        "subscriptions": customer_subscriptions,
        "user_type": "customer",  # Added for dynamic display in HTML
    })


@role_required(["superadmin"])
def delete_admin(request, admin_id):
    if request.method == "POST":
        admin = get_object_or_404(AdminTable, admin_id=admin_id)

        # Prevent deletion of primary superadmin
        if admin.admin_id == 1000000:
            messages.error(request, "Superadmin cannot be deleted.")
            return redirect("superadmin_app:view_admins")

        admin.delete()
        messages.success(request, f"Admin {admin.first_name} {admin.last_name} deleted successfully.")
        return redirect("superadmin_app:view_admins")
    else:
        messages.error(request, "Invalid request method.")
        return redirect("superadmin_app:view_admins")

@role_required(["superadmin", "admin"])
def delete_customer(request, customer_id):
    if request.method == "POST":
        try:
            customer = CustomerTable.objects.get(customer_id=customer_id)
            customer.delete()
            messages.success(request, "Customer deleted successfully.")
        except CustomerTable.DoesNotExist:
            messages.error(request, "Customer not found.")
    return redirect(request.META.get("HTTP_REFERER", "superadmin_app:view_admins"))