from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Avg, Case, When, F
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from django.db import IntegrityError
from paddy_app.decorators import role_required
from paddy_app.helpers import *
from paddy_app.models import *
import json

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
        # Product access information
        'product_access': Subscription.get_admin_product_access(admin_id),
    }
    
    return render(request, "admin_app/admin_dashboard.html", context)

def upgrade_plan(request):
    return render(request, "admin_app/upgrade_plan.html")

@role_required(["admin"])
def upgrade_to_customer(request):
    admin_id = request.session.get('user_id')
    admin = AdminTable.objects.get(admin_id=admin_id)
    
    # Check if admin is already a customer by phone number or email
    existing_customer = CustomerTable.objects.filter(
        Q(email=admin.email) | Q(phone_number=admin.phone_number)
    ).first()

    if request.method == 'POST':
        if existing_customer:
            if existing_customer.email == admin.email:
                messages.info(request, "You are already a customer with this email address.")
            else:
                messages.info(request, "A customer account with this phone number already exists.")
            return redirect('admin_app:admin_dashboard')

        company_name = request.POST.get('company_name')
        gst = request.POST.get('GST')
        address = request.POST.get('address')

        # Validate required fields
        if not company_name or not address:
            messages.error(request, "Company name and address are required.")
            return render(request, 'admin_app/upgrade_to_customer.html', {
                'admin': admin,
                'is_customer': False
            })

        try:
            # Create new customer account
            new_customer = CustomerTable.objects.create(
                admin=admin,  # Link to admin instance, not admin_id
                first_name=admin.first_name,
                last_name=admin.last_name,
                phone_number=admin.phone_number,
                email=admin.email,
                password=admin.password,  # already hashed
                company_name=company_name,
                GST=gst,
                address=address,
            )

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

            messages.success(request, "Successfully upgraded to customer account with 1 month free subscription!")
            return redirect('admin_app:admin_dashboard')

        except IntegrityError as e:
            if 'phone_number' in str(e):
                messages.error(request, "A customer with this phone number already exists.")
            elif 'email' in str(e):
                messages.error(request, "A customer with this email already exists.")
            else:
                messages.error(request, f"Database error: {str(e)}")
            return render(request, 'admin_app/upgrade_to_customer.html', {
                'admin': admin,
                'is_customer': False
            })
        except Exception as e:
            messages.error(request, f"An error occurred while upgrading account: {str(e)}")
            return render(request, 'admin_app/upgrade_to_customer.html', {
                'admin': admin,
                'is_customer': False
            })

    # For GET request, determine if user is already a customer
    is_customer = existing_customer is not None
    return render(request, 'admin_app/upgrade_to_customer.html', {
        'admin': admin, 
        'is_customer': is_customer
    })

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
            return redirect('admin_app:admin_add_subscription') # Redirect to show updated status in content section

    context = {
        "user_count": user_count,
        "added_count": user_count + 50, # Potential count after upgrade
        "existing_subscription_obj": existing_subscription, # Pass the whole object
        # The following are for compatibility with the original template structure, but using existing_subscription_obj is cleaner
        "existing_subscription": 1 if existing_subscription else 0, 
        "payment_amount": existing_subscription.payment_amount if existing_subscription and existing_subscription.payment_amount else 0,
        "subscription_status": existing_subscription.subscription_status if existing_subscription else -1, # -1 for no subscription history
    }
    return render(request, "admin_app/admin_add_subscription.html", context)

@role_required(["admin"])
def admin_customer_list(request):
    admin_id = request.session.get("user_id")  # session must store admin_id during login
    if not admin_id:
        return redirect('login_app:login')  # redirect if not logged in

    # Fetch customers for the current admin
    customers = CustomerTable.objects.filter(admin_id=admin_id)

    return render(request, "admin_app/admin_customer_list.html", {"customers": customers})