from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from paddy_app.models import *
from django.db import IntegrityError
from datetime import date, datetime, timedelta
from django.core.paginator import Paginator
from django.utils import timezone
from paddy_app.decorators import role_required
from paddy_app.helpers import *
from paddy_app.helpers import create_notification
import json
from django.utils.timezone import now
import razorpay
from django.conf import settings
from django.db.models import Q, Sum, Count, Avg, Prefetch
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from django.db.models import Case, When
from dotenv import load_dotenv
import os

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

# Admin Views moved from paddy_app

def admin_dashboard(request):
    from django.db.models import Sum, Count, Q, Avg
    from datetime import datetime, timedelta
    
    # Get admin from session - using 'user_id' key as set in login
    admin_id = request.session.get('user_id')
    if not admin_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login:login')
    
    try:
        admin = AdminTable.objects.get(admin_id=admin_id)
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found. Please log in again.")
        return redirect('login:login')
    
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
    
    return render(request, "admin_app/admin_dashboard.html", context)

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
        "RAZORPAY_KEY_ID": RAZORPAY_KEY_ID, # Pass Razorpay Key for JS in template
    }
    return render(request, "admin_app/admin_add_subscription.html", context)

@role_required(["admin"])
def admin_orders(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if not user_id or not role:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        orders_query = Orders.objects.all()

        if role == 'admin':
            # Admins can only see orders associated with their customers
            try:
                admin_instance = AdminTable.objects.get(admin_id=user_id)
                customer_ids_for_admin = CustomerTable.objects.filter(admin=admin_instance).values_list('customer_id', flat=True)
                orders_query = orders_query.filter(customer__customer_id__in=customer_ids_for_admin)
            except AdminTable.DoesNotExist:
                return JsonResponse({'error': 'Admin not found'}, status=404)

        # Apply filters from query parameters
        status_filter = request.GET.get('status', 'all')
        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')
        category_filter = request.GET.get('category', 'all')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-order_id') # Default sort by latest order

        # Status filter
        if status_filter == 'completed':
            orders_query = orders_query.filter(delivery_status=1)
        elif status_filter == 'ongoing':
            orders_query = orders_query.filter(delivery_status=0)
        elif status_filter == 'pending_payment':
            orders_query = orders_query.filter(payment_status=0)
        elif status_filter == 'recent':
            seven_days_ago = timezone.now().date() - timedelta(days=7)
            orders_query = orders_query.filter(order_date__gte=seven_days_ago)

        # Date range filter
        if date_from_str:
            try:
                date_from = date.fromisoformat(date_from_str)
                orders_query = orders_query.filter(order_date__gte=date_from)
            except ValueError:
                pass # Invalid date format, ignore filter
        if date_to_str:
            try:
                date_to = date.fromisoformat(date_to_str)
                orders_query = orders_query.filter(order_date__lte=date_to)
            except ValueError:
                pass # Invalid date format, ignore filter

        # Category filter
        if category_filter != 'all':
            try:
                category_id = int(category_filter)
                orders_query = orders_query.filter(product_category_id=category_id)
            except ValueError:
                pass # Invalid category ID, ignore filter

        # Search filter (order ID, customer ID, customer name)
        if search_query:
            orders_query = orders_query.filter(
                Q(order_id__icontains=search_query) |
                Q(customer__customer_id__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )

        if request.GET.get('pending_cash') == 'true':
            orders_with_pending_cash = CashPaymentRequest.objects.filter(
                status=0  # Pending status
            ).values_list('order_id', flat=True)
            
            orders_query = orders_query.filter(order_id__in=orders_with_pending_cash)
                # Apply sorting
            orders_query = orders_query.order_by(sort_by)

        cash_payment_requests = []
        
        orders_data = []
        for order in orders_query:
            order_items_data = []
            if order.product_category_id == 3: # Assuming 3 is for multiple items
                for item in order.items.all():
                    order_items_data.append({
                        'product_name': item.product_name,
                        'batch_number': item.batch_number,
                        'expiry_date': str(item.expiry_date),
                        'quantity': item.quantity,
                        'price_per_unit': float(item.price_per_unit),
                        'total_amount': float(item.total_amount),
                        'unit': item.unit,
                    })
            else:
                # For single item orders, infer product name
                product_name = "Paddy" if order.product_category_id == 2 else "Rice" if order.product_category_id == 1 else "Unknown"
                order_items_data.append({
                    'product_name': product_name,
                    'quantity': order.quantity,
                    'price_per_unit': float(order.price_per_unit),
                    'total_amount': float(order.overall_amount),
                    'batch_number': 'N/A', # Not applicable for single items based on current model
                    'expiry_date': 'N/A', # Not applicable for single items based on current model
                    'unit': 'N/A', # Not applicable for single items based on current model
                })

            customer_full_name = f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A"
            
            for req in CashPaymentRequest.objects.filter(order=order).select_related('processed_by'):
                cash_req_data = {
                    'request_id': req.request_id,
                    'amount': float(req.amount),
                    'reference': req.reference,
                    'notes': req.notes,
                    'status': req.status,
                    'created_at': req.created_at.isoformat(),
                }
                
                if req.processed_at:
                    cash_req_data['processed_at'] = req.processed_at.isoformat()
                    
                if req.processed_by:
                    cash_req_data['processed_by_name'] = f"{req.processed_by.first_name} {req.processed_by.last_name}"
                    
                cash_payment_requests.append(cash_req_data)

            orders_data.append({
                'order_id': order.order_id,
                'customer_id': order.customer.customer_id if order.customer else None,
                'customer_full_name': customer_full_name,
                'admin_id': order.admin.admin_id if order.admin else None,
                'payment_status': order.payment_status,
                'delivery_status': order.delivery_status,
                'product_category_id': order.product_category_id,
                'category': order.category,
                'quantity': float(order.quantity),
                'price_per_unit': float(order.price_per_unit),
                'overall_amount': float(order.overall_amount),
                'GST': order.GST,
                'lorry_number': order.lorry_number,
                'driver_name': order.driver_name,
                'driver_ph_no': order.driver_ph_no,
                'order_date': str(order.order_date),
                'paid_amount': float(order.paid_amount) if order.paid_amount is not None else 0.0,
                'order_items': order_items_data,
                'category': order.category,
                'cash_payment_requests': cash_payment_requests,
            })
        return JsonResponse({'orders': orders_data})

    return render(request, "admin_app/admin_orders.html")

    

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
        return render(request, 'admin_app/upgrade_to_customer.html', {'admin': admin, 'is_customer': is_customer})

    return render(request, 'admin_app/upgrade_to_customer.html', {'admin': admin, 'is_customer': is_customer})

def admin_subscription_payment(request):
    return render(request, 'admin_subscription_payment.html')

def admin_subscription_success(request):
    return render(request, 'admin_subscription_success.html')

def admin_select_subscription_plan(request):
    return render(request, 'admin_select_subscription_plan.html')

def upgrade_to_admin(request):
    return render(request, 'upgrade_to_admin.html')

def view_admins(request):
    return render(request, 'view_admins.html')

@role_required(["superadmin", "admin"])
def create_customer(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        gst = request.POST.get("gst")
        address = request.POST.get("address")

        admin_id = request.session.get("user_id")
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login_app:login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login_app:login")

        current_customer_count = CustomerTable.objects.filter(admin=admin).count()
        if current_customer_count >= admin.user_count:
            # Create notification for user limit reached
            create_notification(
                user_type='admin',
                user_id=admin_id,
                notification_type='user_limit_reached',
                title='User Limit Reached',
                message=f'You have reached your customer limit of {admin.user_count}. Please upgrade to add more customers.',
            )
            messages.error(request, "Customer limit reached for your account!")
            return redirect("superadmin_app:onboard" if is_superadmin else "admin_app:customer_onboard")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("superadmin_app:onboard" if is_superadmin else "admin_app:customer_onboard")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("superadmin_app:onboard" if is_superadmin else "admin_app:customer_onboard")

        # GST validation (you'll need to import this function)
        if gst:  # Simple validation for now
            messages.error(request, "Invalid GST number format!")
            return redirect("superadmin_app:onboard" if is_superadmin else "admin_app:customer_onboard")

        try:
            customer = CustomerTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=make_password(password),
                company_name=company_name,
                GST=gst if gst else None,
                address=address,
                admin=admin,
            )

            # Create default 1-month free subscription for customer
            Subscription.objects.create(
                customer_id=customer,
                subscription_type="customer",
                subscription_status=1,
                payment_amount=0,
                start_date=now().date(),
                end_date=now().date() + timedelta(days=30)
            )

            messages.success(request, "Customer created successfully!")
            return redirect("superadmin_app:onboard" if is_superadmin else "admin_app:customer_onboard")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "onboarding_app/onboard.html" if is_superadmin else "customer_onboard.html")

@role_required(["admin"])
def customer_onboard_view(request):
    return render(request, "customer_onboard.html")

@role_required(["admin"])
def admin_notifications(request):
    admin_id = request.session.get('user_id')
    if not admin_id:
        return redirect('login_app:login')
    
    # Get notifications for this admin
    notifications = Notification.objects.filter(
        user_type='admin',
        user_id=admin_id
    ).order_by('-created_at')
    
    context = {
        'notifications': notifications
    }
    return render(request, 'admin_notifications.html', context)

# Profile view moved to profile_app/views.py

@require_POST # Ensures this view only accepts POST requests
@csrf_exempt # Razorpay sends POST here without CSRF token from client-side handler
@role_required(["admin"]) # Protect the endpoint
def create_admin_user_increase_order(request):
    """
    Creates a Razorpay order for an admin's user count increase subscription.
    This is called via AJAX when the admin clicks the "Pay Now" button.
    """
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated.'}, status=401)

        admin = get_object_or_404(AdminTable, admin_id=user_id)
        # Find an approved subscription (status 1) for this admin that needs payment
        subscription = UserIncreaseSubscription.objects.filter(admin_id=admin, subscription_status=1).order_by('-sid').first()

        if not subscription:
            return JsonResponse({'success': False, 'message': 'No approved subscription upgrade found pending payment.'}, status=404)

        if not subscription.payment_amount or subscription.payment_amount <= 0:
            return JsonResponse({'success': False, 'message': 'Payment amount has not been set for this subscription by the superadmin.'}, status=400)

        amount_in_paise = int(subscription.payment_amount * 100)

        razorpay_order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': f'admin_increase_sub_{subscription.sid}_{timezone.now().timestamp()}',
            'payment_capture': '1', # Auto capture payment
            'notes': {
                'subscription_id': subscription.sid,
                'admin_id': user_id,
                'purpose': 'Admin User Count Increase Subscription'
            }
        }
        razorpay_order = client.order.create(data=razorpay_order_data)

        # Store necessary details in session for the verification step
        request.session['user_increase_sub_id'] = subscription.sid  # Store actual subscription ID
        request.session['user_increase_payment_amount'] = float(subscription.payment_amount)
        request.session['user_increase_razorpay_order_id'] = razorpay_order['id']

        return JsonResponse({
            'success': True,
            'key_id': RAZORPAY_KEY_ID,
            'amount': amount_in_paise, # This is what Razorpay checkout will use
            'razorpay_order_id': razorpay_order['id'],
            # Prefill data for Razorpay form
            'admin_name': f"{admin.first_name} {admin.last_name}",
            'admin_email': admin.email,
            'admin_phone': admin.phone_number
        })

    except AdminTable.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Admin user not found.'}, status=404)
    except UserIncreaseSubscription.DoesNotExist: # Should not happen if logic is correct, but good to have
        return JsonResponse({'success': False, 'message': 'Subscription record not found.'}, status=404)
    except Exception as e:
        print(f"Error in create_admin_user_increase_order: {e}") # Log the error for debugging
        return JsonResponse({'success': False, 'message': f'An error occurred while creating payment order: {str(e)}'}, status=500)

@require_POST # Ensures this view only accepts POST requests
@csrf_exempt # Razorpay sends POST here without CSRF token from client-side handler
@role_required(["admin"]) # Protect the endpoint
def verify_admin_user_increase_payment(request):
    """
    Verifies the Razorpay payment signature and updates the subscription
    and admin's user count upon successful payment.
    Also creates a record in the Payments model.
    """
    try:
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        client_razorpay_order_id = data.get('razorpay_order_id') # Order ID from Razorpay's response
        razorpay_signature = data.get('razorpay_signature')

        # Retrieve details stored in session during order creation
        subscription_sid = request.session.get('user_increase_sub_id')
        expected_amount = request.session.get('user_increase_payment_amount')
        session_razorpay_order_id = request.session.get('user_increase_razorpay_order_id')

        if not all([subscription_sid, expected_amount, session_razorpay_order_id, razorpay_payment_id, client_razorpay_order_id, razorpay_signature]):
            return JsonResponse({'success': False, 'message': 'Payment verification failed: Essential data missing from session or request.'}, status=400)

        if client_razorpay_order_id != session_razorpay_order_id:
            return JsonResponse({'success': False, 'message': 'Payment verification failed: Order ID mismatch.'}, status=400)

        params_dict = {
            'razorpay_order_id': session_razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        # Verify the payment signature
        client.utility.verify_payment_signature(params_dict)

        # Optional: Fetch payment details from Razorpay for an additional check on amount and status
        # This adds an extra layer of security and confirms payment details with Razorpay directly.
        payment_details_from_razorpay = client.payment.fetch(razorpay_payment_id)
        if payment_details_from_razorpay['amount'] / 100 != expected_amount:
             return JsonResponse({'success': False, 'message': f'Payment verification failed: Amount mismatch. Expected {expected_amount}, paid {payment_details_from_razorpay["amount"] / 100}'}, status=400)
        if payment_details_from_razorpay['status'] != 'captured':
            # This case should ideally be handled by Razorpay's webhook if payment capture is delayed.
            # For immediate capture ('payment_capture': '1'), this check is a good safeguard.
            return JsonResponse({'success': False, 'message': 'Payment not successfully captured by Razorpay according to their API.'}, status=400)


        # If signature is verified and payment is captured, proceed to update your database
        subscription = get_object_or_404(UserIncreaseSubscription, sid=subscription_sid)
        
        if subscription.subscription_status != 1: # Ensure it was 'approved, pending payment' (status 1)
            # This prevents reprocessing or processing a non-payable subscription
            return JsonResponse({'success': False, 'message': 'Subscription is not in a payable state or has already been processed.'}, status=400)

        admin_user = get_object_or_404(AdminTable, admin_id=subscription.admin_id_id)

        # --- Create Payment Record ---
        try:
            Payments.objects.create(
                # 'order' field will be None as this is not tied to a product order
                # If your Payments model requires 'order', you might need to adjust the model
                # or create a different logging mechanism for subscription payments.
                order=None, 
                amount=expected_amount, # The actual amount paid for the subscription
                date=timezone.now().date(),
                reference=f"user_increase_sub_{subscription_sid}", # Custom reference
                proof_link=razorpay_payment_id, # Store Razorpay Payment ID as proof
                payment_method="Razorpay",
                # You might want to add a field to Payments model to link to AdminTable or CustomerTable directly
                # e.g., paid_by_admin=admin_user
            )
        except Exception as e:
            # Log this error, but don't necessarily fail the whole transaction if payment was successful
            # This depends on how critical the Payments record is for your immediate flow.
            print(f"Error creating payment record for admin subscription {subscription_sid}: {e}")
            messages.warning(request, "Payment was successful, but there was an issue recording the payment details. Please contact support.")


        # Update subscription status to 'Paid and Processed' (e.g., status 3)
        subscription.subscription_status = 3 # Assuming 3 means 'Paid and Processed'
        # You might want to add a field to UserIncreaseSubscription to store razorpay_payment_id
        # subscription.razorpay_payment_id = razorpay_payment_id 
        subscription.save()        # Increase admin's user count
        admin_user.user_count += 50 # Or whatever the agreed increase is
        admin_user.save()

        # Create notifications for user limit upgrade
        create_notification(
            user_type='admin',
            user_id=admin_user.admin_id,
            notification_type='subscription_upgrade',
            title='User Limit Increased',
            message=f'Your user limit has been successfully increased by 50. Payment of ₹{expected_amount} processed.',
            related_subscription_id=subscription_sid
        )

        # Notification for superadmin
        create_notification(
            user_type='superadmin',
            user_id='1000000',  # Super admin ID
            notification_type='subscription_upgrade',
            title='Admin User Limit Upgrade',
            message=f'Admin {admin_user.first_name} {admin_user.last_name} upgraded user limit by 50 users. Payment: ₹{expected_amount}',
            related_subscription_id=subscription_sid
        )

        # Clear the session variables used for this payment to prevent reuse
        if 'user_increase_sub_id' in request.session: del request.session['user_increase_sub_id']
        if 'user_increase_payment_amount' in request.session: del request.session['user_increase_payment_amount']
        if 'user_increase_razorpay_order_id' in request.session: del request.session['user_increase_razorpay_order_id']
        
        messages.success(request, "Payment successful! Your user limit has been increased by 50.")
        return JsonResponse({'success': True, 'message': 'Payment successful and subscription updated.'})

    except razorpay.errors.SignatureVerificationError:
        # Log this error
        print(f"Razorpay Signature Verification Error for order {session_razorpay_order_id if 'session_razorpay_order_id' in locals() else 'UNKNOWN'}")
        return JsonResponse({'success': False, 'message': 'Payment verification failed: Invalid signature.'}, status=400)
    except UserIncreaseSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subscription record not found during verification.'}, status=404)
    except AdminTable.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Admin record not found during verification.'}, status=404)
    except Exception as e:
        print(f"Error in verify_admin_user_increase_payment: {e}") # Log the error for debugging
        # Include more context in error logging if possible, like session_razorpay_order_id
        return JsonResponse({'success': False, 'message': f'An error occurred during payment verification: {str(e)}'}, status=500)


@role_required(["superadmin", "admin"])
def customers_under_admin(request):
    admin_id = request.session.get("user_id")  # session must store admin_id during login
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"
    if not admin_id:
        return redirect('login_app:login')  # redirect if not logged in

    # Fetch customers for the current admin
    customers = CustomerTable.objects.filter(admin_id=admin_id)

    return render(request, "superadmin_app/customers_list.html" if is_superadmin else "admin_app/admin_customer_list.html", {"customers": customers})


@role_required(["admin"])
def payment_success(request):
    """
    Handles successful admin subscription payments.
    Assuming client-side has confirmed Razorpay success and redirects here.
    """
    admin_id = request.session.get("user_id")
    if not admin_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect("login_app:login")
    
    # Check if necessary session variables are present
    amount = request.session.get("subscription_amount")
    days = request.session.get("subscription_days")
    razorpay_order_id = request.session.get("razorpay_order_id")
    
    if not all([amount, days, razorpay_order_id]):
        messages.error(request, "Payment data missing. Please try again.")
        return redirect("admin:admin_dashboard")
    
    try:
        admin_instance = AdminTable.objects.get(admin_id=admin_id)
        
        # Check if there's an existing subscription to update
        existing_subscription = Subscription.objects.filter(
            admin_id=admin_instance,
            subscription_type="admin"
        ).order_by("-end_date").first()
        
        if existing_subscription:
            # Extend existing subscription
            if existing_subscription.end_date and existing_subscription.end_date >= now().date():
                # Subscription still active, extend from end date
                start_date = existing_subscription.end_date + timedelta(days=1)
            else:
                # Subscription expired, start from today
                start_date = now().date()
                
            existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1)
            existing_subscription.payment_amount = float(amount)
            existing_subscription.subscription_status = 1  # Active
            existing_subscription.save()
            
            messages.success(request, "Subscription extended successfully!")
        else:
            # Create new subscription
            Subscription.objects.create(
                admin_id=admin_instance,
                subscription_type="admin",
                payment_amount=float(amount),
                start_date=now().date(),
                end_date=now().date() + timedelta(days=int(days)) - timedelta(days=1),
                subscription_status=1  # Active
            )
            
            messages.success(request, "Subscription created successfully!")
        
        # Create notification for admin
        create_notification(
            user_type='admin',
            user_id=admin_id,
            notification_type='subscription_payment',
            title='Subscription Payment Successful',
            message=f'Your subscription payment of ₹{amount} was successful. Valid for {days} days.',
        )
        
        # Create notification for superadmin
        create_notification(
            user_type='superadmin',
            user_id='1000000',  # Superadmin ID
            notification_type='admin_subscription',
            title='Admin Subscription Payment',
            message=f'Admin {admin_instance.first_name} {admin_instance.last_name} made a subscription payment of ₹{amount} for {days} days.',
        )
        
        # Clear session variables
        if "subscription_amount" in request.session: del request.session["subscription_amount"]
        if "subscription_days" in request.session: del request.session["subscription_days"]
        if "razorpay_order_id" in request.session: del request.session["razorpay_order_id"]
        
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin account not found.")
    except Exception as e:
        messages.error(request, f"Error processing subscription: {str(e)}")
    
    return redirect("admin:admin_dashboard")


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

@role_required(["superadmin", "admin"])
def admin_place_order(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login_app:login")

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    
    # COMMENTED OUT: Razorpay payment verification callback
    """
    if request.method == "POST" and request.POST.get("razorpay_payment_id"):
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")
        temp_data_json = request.session.get("temp_order_data")
        
        if not temp_data_json:
            messages.error(request, "Order data not found. Please try again.")
            return redirect("admin_app:admin_place_order")
        
        temp_data = json.loads(temp_data_json)
        
        # Verify payment
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            
            # Create payment record for booking fee
            payment = Payments.objects.create(
                order=None,  # Will be updated after order creation
                amount=10,
                date=timezone.now().date(),
                reference=payment_id,
                proof_link=payment_id,  # Razorpay payment ID as proof
                payment_method="Razorpay"
            )
            
            # Now proceed with order creation
            if temp_data["product_category_id"] != "3":                # Regular order flow
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                gst = customer.GST

                quantity = float(temp_data["quantity"]) if temp_data["quantity"] else 0
                price_per_unit = float(temp_data["price_per_unit"]) if temp_data["price_per_unit"] else 0
                overall_amount = quantity * price_per_unit

                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    delivery_status=0,
                    product_category_id=temp_data["product_category_id"],
                    category=temp_data.get("category"),  # Add category field
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    overall_amount=overall_amount,
                    GST=gst,
                    lorry_number=temp_data["lorry_number"],
                    driver_name=temp_data["driver_name"],
                    delivery_date=temp_data["delivery_date"],
                    driver_ph_no=temp_data["driver_ph_no"],
                    order_date=date.today()
                )
                  # Update payment with order ID
                payment.order = order
                payment.save()
                
                # Create notifications for order placement
                product_name = "Rice" if temp_data["product_category_id"] == "1" else "Paddy"
                
                # Notification for customer
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Placed',
                    message=f'Your {product_name} order #{order.order_id} has been placed successfully. Quantity: {quantity}, Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Received',
                    message=f'New {product_name} order #{order.order_id} from {customer.first_name} {customer.last_name}. Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, "Order placed successfully after booking fee payment!")
                
            else:
                # Multiple products order flow
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                gst = customer.GST
                  # Create order
                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    quantity=0,
                    product_category_id=temp_data["product_category_id"],
                    category=temp_data.get("category"),  # Add category field
                    GST=gst,
                    lorry_number=temp_data["lorry_number"],
                    driver_name=temp_data["driver_name"],
                    delivery_date=temp_data["delivery_date"],
                    delivery_status=0,
                    driver_ph_no=temp_data["driver_ph_no"],
                    order_date=date.today()
                )
                
                # Update payment with order ID
                payment.order = order
                payment.save()
                
                # Process each order item
                product_names = temp_data["product_names"]
                batch_numbers = temp_data["batch_numbers"]
                expiry_dates = temp_data["expiry_dates"]
                quantities = temp_data["quantities"]
                prices = temp_data["prices"]
                units = temp_data["units"]
                totals = temp_data["totals"]
                
                # Create order items
                order_items = []
                for i in range(len(product_names)):
                    # Skip empty rows
                    if not product_names[i].strip():
                        continue
                        
                    item = OrderItems(
                        order=order,
                        product_name=product_names[i],
                        batch_number=batch_numbers[i],
                        expiry_date=expiry_dates[i],
                        quantity=int(float(quantities[i])),
                        price_per_unit=float(prices[i]),
                        total_amount=float(totals[i]),
                        unit=units[i]
                    )
                    order_items.append(item)
                
                order.overall_amount = sum(float(totals[i]) for i in range(len(totals)) if totals[i].strip())
                order.save()
                  # Bulk create items
                OrderItems.objects.bulk_create(order_items)
                
                # Create notifications for pesticide order
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Placed',
                    message=f'Your pesticide order #{order.order_id} with multiple items has been placed successfully. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Received',
                    message=f'New pesticide order #{order.order_id} from {customer.first_name} {customer.last_name} with {len(order_items)} items. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, "Order with multiple items placed successfully after booking fee payment!")
            
            # Clear temporary data
            if "temp_order_data" in request.session:
                del request.session["temp_order_data"]
                
            return redirect("admin_app:admin_place_order")
            
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect("admin_app:admin_place_order")
    """
    
    # COMMENTED OUT: AJAX request for creating Razorpay order  
    """
    elif request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Store order data temporarily
        temp_data = {}
        
        if str(request.POST.get("product_category_id")) != "3":
            # Regular order
            temp_data = {
                "customer_id": request.POST.get("customer"),
                "product_category_id": request.POST.get("product_category_id"),
                "category": request.POST.get("category"),  # Add category field
                "quantity": request.POST.get("quantity"),
                "price_per_unit": request.POST.get("price_per_unit"),
                "lorry_number": request.POST.get("vehicle_number"),
                "driver_name": request.POST.get("driver_name"),
                "driver_ph_no": request.POST.get("driver_ph_no"),
                "delivery_date": request.POST.get("delivery_date")
            }
            
        else:
            # Multiple products order
            temp_data = {
                "customer_id": request.POST.get("customer"),
                "product_category_id": request.POST.get("product_category_id"),
                "category": request.POST.get("category"),  # Add category field
                "lorry_number": request.POST.get("vehicle_number"),
                "driver_name": request.POST.get("driver_name"),
                "driver_ph_no": request.POST.get("driver_ph_no"),
                "delivery_date": request.POST.get("delivery_date"),
                "product_names": request.POST.getlist("product_name[]"),
                "batch_numbers": request.POST.getlist("batch_number[]"),
                "expiry_dates": request.POST.getlist("expiry_date[]"),
                "quantities": request.POST.getlist("quantity[]"),
                "prices": request.POST.getlist("price_per_unit[]"),
                "units": request.POST.getlist("unit[]"),
                "totals": request.POST.getlist("total_amount[]")
            }
        
        # Store data in session
        request.session["temp_order_data"] = json.dumps(temp_data)
        
        # Create Razorpay order for booking fee
        try:
            razorpay_order = client.order.create({
                "amount": 1000,  # 10 Rs in paise
                "currency": "INR",
                "payment_capture": 1,  # Auto-capture
                "notes": {
                    "purpose": "Order booking fee",
                    "admin_id": str(admin_id)
                }
            })
            
            # Return JSON response for AJAX
            return JsonResponse({
                "status": "success",
                "razorpay_key": RAZORPAY_KEY_ID,
                "order_id": razorpay_order["id"],
                "amount": 10  # In Rs
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Error creating payment: {str(e)}"
            })
    """
    
    # SIMPLE DIRECT ORDER CREATION (WITHOUT PAYMENT)
    if request.method == "POST":
        try:
            if str(request.POST.get("product_category_id")) != "3":
                # Regular order flow (Rice/Paddy)
                customer = CustomerTable.objects.get(customer_id=request.POST.get("customer"))
                
                quantity = float(request.POST.get("quantity")) if request.POST.get("quantity") else 0
                price_per_unit = float(request.POST.get("price_per_unit")) if request.POST.get("price_per_unit") else 0
                overall_amount = quantity * price_per_unit

                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    delivery_status=0,
                    product_category_id=request.POST.get("product_category_id"),
                    category=request.POST.get("category"),
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    overall_amount=overall_amount,
                    GST=customer.GST,
                    lorry_number=request.POST.get("vehicle_number"),
                    driver_name=request.POST.get("driver_name"),
                    delivery_date=request.POST.get("delivery_date"),
                    driver_ph_no=request.POST.get("driver_ph_no"),
                    order_date=date.today()
                )
                
                # Create notifications for order placement
                product_name = "Rice" if request.POST.get("product_category_id") == "1" else "Paddy"
                
                # Notification for customer
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Placed',
                    message=f'Your {product_name} order #{order.order_id} has been placed successfully. Quantity: {quantity}, Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Received',
                    message=f'New {product_name} order #{order.order_id} from {customer.first_name} {customer.last_name}. Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, f"{product_name} order placed successfully!")
                
            else:
                # Multiple products order flow (Pesticides)
                customer = CustomerTable.objects.get(customer_id=request.POST.get("customer"))
                
                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    quantity=0,
                    product_category_id=request.POST.get("product_category_id"),
                    category=request.POST.get("category"),
                    GST=customer.GST,
                    lorry_number=request.POST.get("vehicle_number"),
                    driver_name=request.POST.get("driver_name"),
                    delivery_date=request.POST.get("delivery_date"),
                    delivery_status=0,
                    driver_ph_no=request.POST.get("driver_ph_no"),
                    order_date=date.today()
                )
                
                # Process each order item
                product_names = request.POST.getlist("product_name[]")
                batch_numbers = request.POST.getlist("batch_number[]")
                expiry_dates = request.POST.getlist("expiry_date[]")
                quantities = request.POST.getlist("quantity[]")
                prices = request.POST.getlist("price_per_unit[]")
                units = request.POST.getlist("unit[]")
                totals = request.POST.getlist("total_amount[]")
                
                # Create order items
                order_items = []
                for i in range(len(product_names)):
                    # Skip empty rows
                    if not product_names[i].strip():
                        continue
                        
                    item = OrderItems(
                        order=order,
                        product_name=product_names[i],
                        batch_number=batch_numbers[i],
                        expiry_date=expiry_dates[i],
                        quantity=int(float(quantities[i])),
                        price_per_unit=float(prices[i]),
                        total_amount=float(totals[i]),
                        unit=units[i]
                    )
                    order_items.append(item)
                
                # Bulk create items
                OrderItems.objects.bulk_create(order_items)
                
                order.overall_amount = sum(float(totals[i]) for i in range(len(totals)) if totals[i].strip())
                order.save()
                
                # Create notifications for pesticide order
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Placed',
                    message=f'Your pesticide order #{order.order_id} with multiple items has been placed successfully. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Received',
                    message=f'New pesticide order #{order.order_id} from {customer.first_name} {customer.last_name} with {len(order_items)} items. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, "Pesticide order with multiple items placed successfully!")
            
            return redirect("admin_app:admin_place_order")
            
        except Exception as e:
            messages.error(request, f"Error placing order: {str(e)}")
            return redirect("admin_app:admin_place_order")
    
    # Render the initial form
    return render(request, "admin_app/admin_place_order.html", {"customers": customers})


@role_required(["admin"])
def upgrade_plan(request):
    return redirect("admin_app:admin_subscription_payment")

def upgrade_success(request):
    """
    Display upgrade success page after successful plan upgrade
    """
    return render(request, 'admin_app/upgrade_success.html')
