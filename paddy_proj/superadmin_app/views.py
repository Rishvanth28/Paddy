from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import date, timedelta
from django.db.models import Q
from paddy_app.models import AdminTable, CustomerTable, Subscription, UserIncreaseSubscription, Orders, Payments, OrderItems
from paddy_app.decorators import role_required
from paddy_app.models import Notification
import json
import razorpay
from django.conf import settings
from django.db.models import Q, Sum, Count, Avg
from paddy_app.helpers import create_notification
from django.utils.timezone import now
from dotenv import load_dotenv
import os
from django.core.exceptions import ValidationError
import logging

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

logger = logging.getLogger(__name__)

# Create your views here.

@role_required('superadmin')
def superadmin_dashboard(request):
    """Superadmin dashboard view"""
    from django.db.models import Sum, Count, Avg
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
    
    try:
        # Import Payments model - it might be in paddy_app models
        from paddy_app.models import Payments
        all_payments = Payments.objects.all()
    except ImportError:
        # Handle case where Payments might be defined elsewhere or differently
        all_payments = []
    
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
    if all_payments:
        total_payments = all_payments.aggregate(total=Sum('amount'))['total'] or 0
        successful_payments = all_payments.filter(order__payment_status__in=[1, 2]).count()
    else:
        total_payments = 0
        successful_payments = 0
    
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
    top_product = top_product_data['category'] if top_product_data and top_product_data.get('category') else 'N/A'
    
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
        if order.customer and order.admin:
            recent_activity.append({
                'icon': '📦',
                'text': f'Order #{order.order_id} placed by {order.customer.first_name} {order.customer.last_name} (Admin: {order.admin.first_name})',
                'time': order.order_date.strftime('%d %b %Y')
            })
    
    # Recent payments if available
    if all_payments:
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
            if hasattr(admin, 'created_at') and admin.created_at:
                recent_activity.append({
                    'icon': '👨‍💼',
                    'text': f'New admin {admin.first_name} {admin.last_name} joined the platform',
                    'time': admin.created_at.strftime('%d %b %Y')
                })
    
    # Sort recent activity by time (simplified)
    if recent_activity:
        recent_activity = sorted(
            [a for a in recent_activity if a.get('time') != 'N/A'],
            key=lambda x: datetime.strptime(x['time'], '%d %b %Y') if x.get('time') else datetime.min,
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
        if cat.get('category'):
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
    
    return render(request, 'superadmin_app/superadmin_dashboard.html', context)

@role_required('superadmin')
def superadmin_subscription(request):
    """View admin subscription requests"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    subscriptions_queryset = UserIncreaseSubscription.objects.filter().order_by('-sid')
    
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

@role_required('superadmin')
def superadmin_subscription_review(request):
    """Review admin subscription requests"""
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

@role_required('superadmin')
def super_admin_orders(request):
    """View all orders"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if not user_id or not role:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        orders_query = Orders.objects.all()

        # Apply filters from query parameters
        status_filter = request.GET.get('status', 'all')
        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')
        category_filter = request.GET.get('category', 'all')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-order_id')  # Default sort by latest order

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
                pass  # Invalid date format, ignore filter
        if date_to_str:
            try:
                date_to = date.fromisoformat(date_to_str)
                orders_query = orders_query.filter(order_date__lte=date_to)
            except ValueError:
                pass  # Invalid date format, ignore filter

        # Category filter
        if category_filter != 'all':
            try:
                category_id = int(category_filter)
                orders_query = orders_query.filter(product_category_id=category_id)
            except ValueError:
                pass  # Invalid category ID, ignore filter

        # Search filter (order ID, customer ID, customer name)
        if search_query:
            orders_query = orders_query.filter(
                Q(order_id__icontains=search_query) |
                Q(customer__customer_id__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )

        # Apply sorting
        orders_query = orders_query.order_by(sort_by)

        orders_data = []
        for order in orders_query:
            order_items_data = []
            
            if order.product_category_id == 3:  # Assuming 3 is for multiple items
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
                    'batch_number': 'N/A',  # Not applicable for single items based on current model
                    'expiry_date': 'N/A',  # Not applicable for single items based on current model
                    'unit': 'N/A',  # Not applicable for single items based on current model
                })

            customer_full_name = f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A"

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
            })
        return JsonResponse({'orders': orders_data})

    return render(request, 'superadmin_app/superadmin_orders.html')

@role_required(["superadmin"])
def superadmin_notifications(request):
    """Display notifications for superadmin"""
    admin_id = request.session.get("user_id")
    
    # Get all admin payment and subscription notifications
    notifications = Notification.objects.filter(
        Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
        Q(user_type='superadmin', user_id=str(admin_id))
    ).order_by('-created_at')[:50]
    
    unread_count = Notification.objects.filter(
        Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
        Q(user_type='superadmin', user_id=str(admin_id)),
        is_read=False
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'superadmin_app/superadmin_notifications.html', context)

@role_required('superadmin')
def view_admins(request):
    """View all admins"""
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

@role_required('superadmin')
def view_customers_under_admin(request, admin_id):
    """View customers under a specific admin"""
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

@role_required('superadmin')
def delete_admin(request, admin_id):
    """Delete an admin"""
    if request.method == "POST":
        admin = get_object_or_404(AdminTable, admin_id=admin_id)

        # Prevent deletion of primary superadmin
        if admin.admin_id == 1000000:
            messages.error(request, "Superadmin cannot be deleted.")
            return redirect('superadmin_app:view_admins')

        admin.delete()
        messages.success(request, f"Admin {admin.first_name} {admin.last_name} deleted successfully.")
        return redirect('superadmin_app:view_admins')
    else:
        messages.error(request, "Invalid request method.")
        return redirect('superadmin_app:view_admins')

@role_required('superadmin')
def delete_customer(request, customer_id):
    """Delete a customer"""
    if request.method == "POST":
        try:
            customer = CustomerTable.objects.get(customer_id=customer_id)
            customer.delete()
            messages.success(request, "Customer deleted successfully.")
        except CustomerTable.DoesNotExist:
            messages.error(request, "Customer not found.")
    return redirect(request.META.get("HTTP_REFERER", "superadmin_app:view_admins"))

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

@role_required(["superadmin", "admin"])
def place_order(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login_app:login")

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)

    if request.method == "POST":
        if is_superadmin:
            # Log POST data for debugging
            logger.debug("POST data: %s", request.POST)

            try:
                temp_data = {
                    "customer_id": request.POST.get("customer"),
                    "product_category_id": request.POST.get("product_category_id"),
                    "category": request.POST.get("category"),
                    "quantity": float(request.POST.get("quantity", 0)),
                    "price_per_unit": float(request.POST.get("price_per_unit", 0)),
                    "lorry_number": request.POST.get("vehicle_number"),
                    "driver_name": request.POST.get("driver_name"),
                    "driver_ph_no": request.POST.get("driver_ph_no"),
                    "delivery_date": request.POST.get("delivery_date")
                }

                # Check for missing or invalid fields
                if not temp_data["customer_id"] or not temp_data["product_category_id"] or not temp_data["category"]:
                    raise ValidationError("Missing required fields.")
                if temp_data["quantity"] <= 0 or temp_data["price_per_unit"] <= 0:
                    raise ValidationError("Quantity and price must be positive numbers.")

                # Save order to database
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                order = Orders.objects.create(
                    customer=customer,
                    admin_id=admin_id,
                    payment_status=0,  # Assuming 0 means unpaid
                    overall_amount=temp_data["quantity"] * temp_data["price_per_unit"],
                    product_category_id=temp_data["product_category_id"],
                    category=temp_data["category"],
                    quantity=temp_data["quantity"],
                    price_per_unit=temp_data["price_per_unit"],
                    lorry_number=temp_data["lorry_number"],
                    driver_name=temp_data["driver_name"],
                    driver_ph_no=temp_data["driver_ph_no"],
                    delivery_date=temp_data["delivery_date"],
                    order_date=timezone.now().date(),
                    delivery_status=0  # Assuming 0 means pending
                )

                messages.success(request, f"Order {order.order_id} placed successfully.")
                return redirect("superadmin_app:place_order")

            except ValidationError as e:
                messages.error(request, str(e))
                return redirect("superadmin_app:place_order")

        elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Admin-specific Razorpay logic remains unchanged
            temp_data = {
                "customer_id": request.POST.get("customer"),
                "product_category_id": request.POST.get("product_category_id"),
                "category": request.POST.get("category"),
                "quantity": request.POST.get("quantity"),
                "price_per_unit": request.POST.get("price_per_unit"),
                "lorry_number": request.POST.get("vehicle_number"),
                "driver_name": request.POST.get("driver_name"),
                "driver_ph_no": request.POST.get("driver_ph_no"),
                "delivery_date": request.POST.get("delivery_date")
            }
            request.session["temp_order_data"] = json.dumps(temp_data)
            return JsonResponse({"status": "success"})

    # Render the initial form
    return render(request, "superadmin_app/place_order.html" if is_superadmin else "admin_app/admin_place_order.html", {"customers": customers})

