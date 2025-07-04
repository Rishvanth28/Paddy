from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from .models import *
from django.db import IntegrityError
from datetime import date
from django.core.paginator import Paginator
from django.utils import timezone
from .decorators import role_required
from .helpers import *
from .helpers import create_notification
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
import razorpay
from django.conf import settings
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from dotenv import load_dotenv
import os
from django.db.models import Case, When, Sum, Count, F
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from .models import Orders, OrderItems, Payments, AdminTable, CustomerTable
import os
from django.db.models import Q, Prefetch


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))



@role_required(["admin"])
def admin_dashboard(request):
    from django.db.models import Sum, Count, Q, Avg
    from datetime import datetime, timedelta
    
    # Get admin from session - using 'user_id' key as set in login
    admin_id = request.session.get('user_id')
    if not admin_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
    
    try:
        admin = AdminTable.objects.get(admin_id=admin_id)
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found. Please log in again.")
        return redirect('login_app:login')
    
    # Calculate date ranges
    today = datetime.now().date()
    last_7_days = today - timedelta(days=7)
    current_month_start = today.replace(day=1)
    
    # Get orders data for this admin only
    admin_orders = Orders.objects.filter(admin=admin)
      # Order statistics - only real data, excluding cancelled orders
    total_orders = admin_orders.count()
    completed_orders = admin_orders.filter(delivery_status=1).count()
    pending_orders = admin_orders.filter(delivery_status=0).count()
    new_orders = admin_orders.filter(order_date__gte=last_7_days).count()
    
    # Customer statistics - only customers under this admin
    total_customers = CustomerTable.objects.filter(admin=admin).count()
    
    # Payment statistics - only successful payments, excluding failed payments
    admin_payments = Payments.objects.filter(order__admin=admin)
    total_payments_amount = admin_payments.aggregate(total=Sum('amount'))['total'] or 0
    successful_payments = admin_payments.filter(order__payment_status__in=[1, 2]).count()
    
    # Subscription statistics - only this admin's subscriptions
    active_subscriptions = Subscription.objects.filter(
        admin_id=admin,
        subscription_status=1,
        end_date__gte=today
    ).count()
    
    expiring_subscriptions = Subscription.objects.filter(
        admin_id=admin,
        subscription_status=1,
        end_date__lte=today + timedelta(days=30),
        end_date__gte=today
    ).count()
    
    # Revenue statistics - only from completed/paid orders
    total_revenue = admin_orders.filter(payment_status__in=[1, 2]).aggregate(
        total=Sum('overall_amount')
    )['total'] or 0
    
    # Average order value - only from actual orders
    avg_order_value = 0
    if total_orders > 0:
        avg_order_value = admin_orders.aggregate(avg=Avg('overall_amount'))['avg'] or 0
    
    # Top product (most ordered category) - only from real orders
    top_product = 'N/A'
    if total_orders > 0:
        top_product_data = admin_orders.values('category').annotate(
            count=Count('category')
        ).order_by('-count').first()
        if top_product_data and top_product_data['category']:
            top_product = top_product_data['category']
      # Customer growth - now we can calculate based on created_at field
    customer_growth = "N/A"
    if hasattr(CustomerTable, 'created_at'):
        current_month_customers = CustomerTable.objects.filter(
            admin=admin,
            created_at__gte=current_month_start
        ).count()
        if total_customers > 0:
            growth_percentage = (current_month_customers / total_customers) * 100
            customer_growth = f"{round(growth_percentage, 1)}%"
    
    # Recent activity - only real activity from this admin's data
    recent_activity = []
    
    # Recent orders - limit to last 3 real orders
    recent_orders = admin_orders.order_by('-order_date')[:3]
    for order in recent_orders:
        activity_text = f'Order #{order.order_id} from {order.customer.first_name} {order.customer.last_name}'
        if order.category:
            activity_text += f' - {order.category}'
        recent_activity.append({
            'icon': '📦',
            'text': activity_text,
            'time': order.order_date.strftime('%d %b %Y')
        })
    
    # Recent payments - limit to last 2 real payments
    recent_payments = admin_payments.order_by('-date')[:2]
    for payment in recent_payments:
        order_info = f"Order #{payment.order.order_id}" if payment.order else "N/A"
        recent_activity.append({
            'icon': '💰',
            'text': f'Payment ₹{payment.amount} received for {order_info}',
            'time': payment.date.strftime('%d %b %Y')
        })    # Sort recent activity by date (simplified - in production should use datetime)
    recent_activity = recent_activity[:5]  # Limit to 5 most recent items
    
    # Chart data for analytics
    # Monthly orders data (last 6 months)
    monthly_orders = []
    monthly_revenue = []
    order_categories = []
    category_counts = []
    
    # Get monthly data for last 6 months
    for i in range(6):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_orders = admin_orders.filter(order_date__range=[month_start, month_end]).count()
        month_revenue = admin_orders.filter(
            order_date__range=[month_start, month_end],
            payment_status__in=[1, 2]
        ).aggregate(total=Sum('overall_amount'))['total'] or 0
        
        monthly_orders.insert(0, month_orders)
        monthly_revenue.insert(0, float(month_revenue))
    
    # Category data for pie chart
    categories = admin_orders.values('category').annotate(
        count=Count('category'),
        revenue=Sum('overall_amount')
    ).order_by('-count')
    
    for cat in categories:
        if cat['category']:
            order_categories.append(cat['category'])
            category_counts.append(cat['count'])
    
    # Payment status data
    payment_completed = admin_orders.filter(payment_status=2).count()
    payment_partial = admin_orders.filter(payment_status=1).count()
    payment_pending = admin_orders.filter(payment_status=0).count()    
    # Monthly labels
    month_labels = []
    for i in range(6):
        month_date = (today.replace(day=1) - timedelta(days=i*30))
        month_labels.insert(0, month_date.strftime('%b %Y'))
    
    context = {
        'admin': admin,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'new_orders': new_orders,
        'total_customers': total_customers,
        'total_payments': total_payments_amount,
        'successful_payments': successful_payments,
        'active_subscriptions': active_subscriptions,
        'expiring_subscriptions': expiring_subscriptions,
        'total_revenue': total_revenue,
        'avg_order_value': round(avg_order_value, 2) if avg_order_value else 0,
        'top_product': top_product,
        'customer_growth': customer_growth,
        'recent_activity': recent_activity,
        # Chart data - JSON serialized for JavaScript
        'monthly_orders': json.dumps(monthly_orders),
        'monthly_revenue': json.dumps(monthly_revenue),
        'month_labels': json.dumps(month_labels),
        'order_categories': json.dumps(order_categories),
        'category_counts': json.dumps(category_counts),
        'payment_completed': payment_completed,
        'payment_partial': payment_partial,
        'payment_pending': payment_pending,
    }
    
    return render(request, "admin_dashboard.html", context)

def upgrade_plan(request):
    return render(request, "upgrade_plan.html")

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
    
    return render(request, 'customer_dashboard.html', context)

@role_required(["admin"])
def admin_add_subscription(request):
    user_id = request.session.get("user_id")
    admin = get_object_or_404(AdminTable, admin_id=user_id)
    user_count = admin.user_count
      # Fetch the latest subscription request for this admin
    existing_subscription = UserIncreaseSubscription.objects.filter(admin_id=admin).order_by('-sid').first()

    if request.method == "POST":
        # This part is for submitting a new upgrade request
        if request.POST.get("submission_type") == '0':
            # Prevent new request if one is already active (pending approval or pending payment)
            if existing_subscription and existing_subscription.subscription_status in [0, 1]: # 0: Pending Approval, 1: Approved, Pending Payment
                # Don't add a Django message here - the status will be shown in the content section
                pass
            else:
                try:
                    subscription = UserIncreaseSubscription.objects.create(
                        admin_id=admin,
                        subscription_status=0 # Status 0: Pending Superadmin Approval
                    )
                    
                    # Create notification for superadmin about the new subscription request
                    create_notification(
                        user_type='superadmin',
                        user_id='1000000',  # Super admin ID
                        notification_type='subscription_request',
                        title='New User Limit Upgrade Request',
                        message=f'Admin {admin.first_name} {admin.last_name} has requested a user limit upgrade by 50 users. Please review the request.',
                        related_subscription_id=subscription.sid
                    )
                    
                    # Don't add a Django message here - the status will be shown in the content section
                    pass
                except Exception as e:
                    # Only show error messages as toasts since these are exceptional cases
                    messages.error(request, f"Failed to submit subscription request. Error: {str(e)}")
            return redirect('admin_add_subscription') # Redirect to show updated status in content section

    context = {
        "user_count": user_count,
        "added_count": user_count + 50, # Potential count after upgrade
        "existing_subscription_obj": existing_subscription, # Pass the whole object
        # The following are for compatibility with the original template structure, but using existing_subscription_obj is cleaner
        "existing_subscription": 1 if existing_subscription else 0, 
        "payment_amount": existing_subscription.payment_amount if existing_subscription and existing_subscription.payment_amount else 0,
        "subscription_status": existing_subscription.subscription_status if existing_subscription else -1, # -1 for no subscription history
        "RAZORPAY_KEY_ID": RAZORPAY_KEY_ID, # Pass Razorpay Key for JS in template
    }
    return render(request, "admin_add_subscription.html", context)

@role_required(["customer"])
def upgrade_to_admin(request):
    customer_id = request.session.get('user_id')
    customer = CustomerTable.objects.get(customer_id=customer_id)

    # Check if already admin
    is_admin = AdminTable.objects.filter(email=customer.email).exists()
    
    if is_admin:
        messages.info(request, "You are already an admin! Access denied.")
        return render(request, 'upgrade_to_admin.html', {'customer': customer, 'is_admin': True})

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
        return render(request, 'upgrade_to_admin.html', {'customer': customer, 'is_admin': True})

    return render(request, 'upgrade_to_admin.html', {'customer': customer, 'is_admin': is_admin})

@role_required(["admin"])
def upgrade_to_customer(request):
    admin_id = request.session.get('user_id')
    admin = AdminTable.objects.get(admin_id=admin_id)
    
    # Check if admin is already a customer
    is_customer = CustomerTable.objects.filter(email=admin.email).exists()

    if request.method == 'POST':
        if is_customer:
            messages.info(request, "You are already a customer.")
            return redirect('admin_dashboard')

        company_name = request.POST.get('company_name')
        gst = request.POST.get('GST')
        address = request.POST.get('address')

        new_customer = CustomerTable(
            admin_id=admin.admin_id,  # Linking the admin ID
            first_name=admin.first_name,
            last_name=admin.last_name,
            phone_number=admin.phone_number,
            email=admin.email,
            password=admin.password,  # already hashed
            company_name=company_name,
            GST=gst,
            address=address,
        )
        new_customer.save()

        # ✅ Create default 1-month free subscription for upgraded customer
        Subscription.objects.create(
            customer_id=new_customer,
            subscription_type="customer",
            subscription_status=1,  # Active
            payment_amount=0,  # Free subscription
            start_date=now().date(),
            end_date=now().date() + timedelta(days=30)  # 1 month free
        )

        # Create notification for successful upgrade
        create_notification(
            user_type='customer',
            user_id=new_customer.customer_id,
            notification_type='account_upgrade',
            title='Account Upgraded Successfully',
            message='Your admin account has been upgraded to customer with 1 month free subscription.',
        )

        # Create notification for admin (since they're now also a customer)
        create_notification(
            user_type='admin',
            user_id=admin.admin_id,
            notification_type='account_upgrade',
            title='Upgraded to Customer',
            message='You have successfully upgraded to customer account with 1 month free subscription.',
        )

        messages.success(request, "You have been upgraded to customer successfully with 1 month free subscription!")
        # Update is_customer to True after successful upgrade
        is_customer = True
        return render(request, 'upgrade_to_customer.html', {'admin': admin, 'is_customer': is_customer})

    return render(request, 'upgrade_to_customer.html', {'admin': admin, 'is_customer': is_customer})

    

def profile(request):
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    if not role or not user_id:
        messages.error(request, "Please log in to view your profile.")
        return redirect('login_app:login')
    
    # Determine base template and fetch user data based on role
    if role == 'superadmin':
        base_template = 'superadmin_app/superadmin_base.html'
        try:
            user = AdminTable.objects.get(admin_id=user_id)
            user_data = {
                'user_type': 'Super Admin',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'admin_id': user.admin_id,
                'user_count': user.user_count,
                'created_at': user.created_at,
                'is_superadmin': True,
            }
        except AdminTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
            
    elif role == 'admin':
        base_template = 'admin_base.html'
        try:
            user = AdminTable.objects.get(admin_id=user_id)
            # Get subscription info for admin
            subscription = Subscription.objects.filter(
                admin_id=user, 
                subscription_type="admin"
            ).order_by('-end_date').first()
            
            user_data = {
                'user_type': 'Admin',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'admin_id': user.admin_id,
                'user_count': user.user_count,
                'created_at': user.created_at,
                'subscription': subscription,
                'is_admin': True,
            }
        except AdminTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
            
    elif role == 'customer':
        base_template = 'customer_base.html'
        try:
            user = CustomerTable.objects.get(customer_id=user_id)
            # Get subscription info for customer
            subscription = Subscription.objects.filter(
                customer_id=user, 
                subscription_type="customer"
            ).order_by('-end_date').first()
            
            user_data = {
                'user_type': 'Customer',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'customer_id': user.customer_id,
                'company_name': user.company_name,
                'gst': user.GST,
                'address': user.address,
                'admin': user.admin,
                'created_at': user.created_at,
                'subscription': subscription,
                'is_customer': True,
            }
        except CustomerTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
    else:
        messages.error(request, "Invalid role.")
        return redirect('login_app:login')
    
    context = {
        'base_template': base_template,
        'user_data': user_data,
        'role': role,
    }
    return render(request, 'profile.html', context)

def swap_role(request):
    current_role = request.session.get("role")
    user_id = request.session.get("user_id")

    if current_role == "admin":
        try:
            admin = AdminTable.objects.get(admin_id=user_id)
            customer = CustomerTable.objects.get(phone_number=admin.phone_number)

            # Logout admin
            request.session.flush()

            # Login as customer
            request.session["user_id"] = customer.customer_id
            request.session["role"] = "customer"
            messages.success(request, "Switched to Customer account.")
            return redirect("customer_dashboard")

        except CustomerTable.DoesNotExist:
            messages.warning(request, "You don’t have a Customer account linked. Please subscribe or contact support.")
            return redirect("admin_dashboard")

    elif current_role == "customer":
        try:
            customer = CustomerTable.objects.get(customer_id=user_id)
            admin = AdminTable.objects.get(phone_number=customer.phone_number)

            # Logout customer
            request.session.flush()

            # Login as admin
            request.session["user_id"] = admin.admin_id
            request.session["role"] = "admin"
            messages.success(request, "Switched to Admin account.")
            return redirect("admin_dashboard")

        except AdminTable.DoesNotExist:
            messages.warning(request, "You don’t have an Admin account linked. Please subscribe or contact support.")
            return redirect("customer_dashboard")

    messages.error(request, "Invalid session. Please log in again.")
    return redirect("login_app:login")
