from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from paddy_app.models import *
from django.db import IntegrityError
from datetime import date, datetime, timedelta
from django.core.paginator import Paginator
from django.utils import timezone
from paddy_app.decorators import role_required
from paddy_app.helpers import create_notification, validate_gst, number_to_words_indian
import json
from django.utils.timezone import now
import razorpay
import time
from django.conf import settings
from dotenv import load_dotenv
import os
from django.db.models import Q, Sum, Count

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

@role_required(["customer"])
def customer_dashboard(request):
    from django.db.models import Sum, Count, Q, Avg, Max, F
    from datetime import datetime, timedelta
    import json
    
    # Get customer from session - using 'user_id' key as set in login
    customer_id = request.session.get('user_id')
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login')
    
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
        'completed_delivery': completed_delivery,        
        'pending_payment': pending_payment,
        'partial_payment': partial_payment,
        'completed_payment': completed_payment,
        'recent_orders': recent_orders,        
        'upcoming_deliveries': upcoming_deliveries,
        'category_data_json': json.dumps(category_data),
        'monthly_orders_json': json.dumps(monthly_orders),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'payment_status_json': json.dumps(payment_status_data),
        'delivery_status_json': json.dumps(delivery_status_data)
    }
    
    return render(request, 'customer_app/customer_dashboard.html', context)


@role_required(["customer"])
def customer_orders(request):
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login_app:login')
    
    # Check if it's an AJAX request asking for JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Fetch all orders for this customer
        orders = Orders.objects.filter(customer__customer_id=customer_id).order_by('-order_date')
        
        # Convert to JSON serializable format
        orders_data = [{
            'order_id': order.order_id,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
            'overall_amount': order.overall_amount,
            'paid_amount': order.paid_amount,
            'payment_status': order.payment_status,
            'delivery_status': order.delivery_status,
            'quantity': order.quantity,
            'price_per_unit': float(order.price_per_unit),
            'GST': order.GST,
            'lorry_number': order.lorry_number,
            'driver_name': order.driver_name,
            'driver_ph_no': order.driver_ph_no,
            'product_category_id': order.product_category_id,
            'category': order.category,  # Include category field
        } for order in orders]
        return JsonResponse({'orders': orders_data})
    
    # For regular page load, just render the template (JS will fetch data)
    return render(request, 'customer_app/customer_order.html')

@role_required(["customer"])
def payment(request):
    id = request.POST.get('order_id') or request.GET.get('order_id')
    order = Orders.objects.get(pk=id)
    # Assuming you have a related model for order items/products
    # If not, you'll need to create one to store multiple products per order
    if order.product_category_id == 3:
        order_items = OrderItems.objects.filter(order=order)
        order_items = [{'quantity':item.quantity,'price_per_unit':item.price_per_unit,
                        'total_amount':item.total_amount,'product_name':item.product_name,'unit':item.unit} for item in order_items]
    else:
        order_items = [{'quantity':order.quantity,'price_per_unit':order.price_per_unit,
                        'total_amount':order.overall_amount,'product_name':'Paddy' if order.product_category_id == 2 else 'Rice'}]
    total_amount = order.overall_amount
    
    # Calculate balance due
    paid_amount = order.paid_amount or 0
    balance_due = total_amount - paid_amount
    
    # Determine payment status
    if paid_amount == 0:
        payment_status = 0  # Pending
    elif paid_amount < total_amount:
        payment_status = 1  # Partially Paid
    else:
        payment_status = 2  # Fully Paid
    
    # Calculate payment deadline date
    payment_deadline = order.order_date + timezone.timedelta(days=order.payment_deadline)
    
    context = {
        'order': order,
        'order_name': 'Paddy' if order.product_category_id == 2 else 'Rice' if order.product_category_id == 1 else 'Fertilizer',
        'order_items': order_items,
        'customer': order.customer,
        'total_amount': order.overall_amount,
        'payment_terms': order.payment_deadline,
        'balance_due': balance_due,
        'payment_status': payment_status,
        'invoice_date': order.order_date,
        'total_items': sum(item['quantity'] for item in order_items),
        'invoice_number': f"UFs {order.order_id}",
        'payment_terms': order.payment_deadline,
        'payment_deadline': payment_deadline,
        'amount_in_words': number_to_words_indian(order.overall_amount),
        'business_year': "urakadai "+str(order.order_date.year),
    }
    return render(request, 'customer_app/payment.html',context)

@csrf_exempt
def customer_payment_success(request):
    """
    Handles successful customer subscription payments.
    Assumes client-side has confirmed Razorpay success and sends details.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # IMPORTANT: Expecting razorpay_payment_id from the client's AJAX call
            razorpay_payment_id = data.get('razorpay_payment_id', 'N/A') 

            customer_id = request.session.get("user_id") # Assuming user_id is customer_id for this session
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")
            # session_razorpay_order_id = request.session.get("razorpay_order_id") # Razorpay's order ID from session

            if not all([customer_id, amount, days]):
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            customer_instance = get_object_or_404(CustomerTable, customer_id=customer_id)
            
            # --- Create Payment Record ---
            try:
                Payments.objects.create(
                    order=None, # No direct order for subscriptions
                    amount=float(amount),
                    date=timezone.now().date(),
                    reference=f"cust_sub_{customer_id}_{razorpay_payment_id}",
                    proof_link=razorpay_payment_id,
                    payment_method="Razorpay"
                )
            except Exception as e:
                print(f"Error creating payment record for customer subscription {customer_id}: {e}")
                # Log and continue, or handle as critical error

            existing_subscription = Subscription.objects.filter(
                customer_id=customer_instance, # Use instance here
                subscription_type="customer"
            ).order_by("-end_date").first()

            if existing_subscription:
                start_date = existing_subscription.end_date + timedelta(days=1) if existing_subscription.end_date and existing_subscription.end_date >= now().date() else now().date()
                existing_subscription.start_date = start_date
                existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1) # Inclusive end date
                existing_subscription.payment_amount += float(amount) # Ensure float for amount
                existing_subscription.subscription_status = 1 # Active
                existing_subscription.save()
                message_text = "Subscription extended successfully."
            else:
                Subscription.objects.create(
                    customer_id=customer_instance, # Use instance here
                    subscription_type="customer",
                    payment_amount=float(amount),
                    start_date=now().date(),
                    end_date=now().date() + timedelta(days=int(days)) - timedelta(days=1), # Inclusive end date
                    subscription_status=1 # Active
                )
                message_text = "Subscription created successfully."
            
            # Clear session variables for this subscription payment
            if "subscription_amount" in request.session: del request.session["subscription_amount"]
            if "subscription_days" in request.session: del request.session["subscription_days"]
            if "razorpay_order_id" in request.session: del request.session["razorpay_order_id"]
            # any other relevant session keys

            messages.success(request, message_text) # For next page load
            return JsonResponse({"success": True, "message": message_text})

        except CustomerTable.DoesNotExist:
            return JsonResponse({"success": False, "message": "Customer not found."})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"Error processing customer subscription: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})


def customer_delivery_validation(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        delivery_status = request.POST.get('delivery_status')

        try:
            order = Orders.objects.get(order_id=order_id)
            order.delivery_status = delivery_status
            order.save()
            
            # Create notification for admin when customer marks delivery as complete
            if delivery_status == '1':  # Assuming 1 means delivered
                product_name = "Rice" if order.product_category_id == 1 else "Paddy" if order.product_category_id == 2 else "Pesticide"
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=order.admin.admin_id,
                    notification_type='delivery_confirmed',
                    title='Order Delivery Confirmed',
                    message=f'Customer {order.customer.first_name} {order.customer.last_name} has confirmed delivery of {product_name} order #{order.order_id}.',
                    related_order_id=order.order_id
                )
            
            messages.success(request, "Delivery status updated successfully.")
            return redirect('customer_app:customer_orders')
        except Orders.DoesNotExist:
            return redirect('customer_app:customer_orders')

@role_required('customer')
def customer_onboard(request):
    """Customer onboarding view"""
    return render(request, 'customer_app/onboarding.html')

@role_required('customer')
def customer_notifications(request):
    """View customer notifications"""
    customer_id = request.session.get('user_id')
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
    
    notifications = Notification.objects.filter(
        user_type='customer',
        user_id=customer_id
    ).order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(notifications, 10)  # 10 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'customer_app/customer_notifications.html', {'page_obj': page_obj})

@role_required('customer')
def customer_subscription_payment(request):
    """Handle customer subscription payments"""
    customer_id = request.session.get('user_id')
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
        
    try:
        customer = CustomerTable.objects.get(customer_id=customer_id)
    except CustomerTable.DoesNotExist:
        messages.error(request, "Customer not found. Please log in again.")
        return redirect('login_app:login')
    
    if request.method == 'POST':
        plan = request.POST.get('plan')
        
        if plan == 'monthly':
            amount = 499
            months = 1
        elif plan == 'yearly':
            amount = 4999
            months = 12
        else:
            messages.error(request, "Invalid subscription plan selected.")
            return redirect('customer_app:customer_subscription_payment')
        
        # Create Razorpay order
        data = {
            'amount': int(amount * 100),  # Amount in paise
            'currency': 'INR',
            'receipt': f'sub_customer_{customer.customer_id}_{int(time.time())}',
            'payment_capture': 1  # Auto-capture
        }
        
        razorpay_order = client.order.create(data=data)
        
        # Store in session for later verification
        request.session['subscription_data'] = {
            'amount': amount,
            'months': months,
            'razorpay_order_id': razorpay_order['id']
        }
        
        context = {
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': RAZORPAY_KEY_ID,
            'customer': customer,
            'amount': amount,
            'callback_url': request.build_absolute_uri('/customer-app/payment-success/')
        }
        
        return render(request, 'customer_app/subscription_payment.html', context)
    
    # Just show the subscription plans page
    return render(request, 'customer_app/select_subscription_plan.html')

@role_required('customer')
def customer_select_subscription_plan(request):
    """Show subscription plan selection page"""
    return render(request, 'customer_app/select_subscription_plan.html')

@role_required('customer')
def customers_list(request):
    """View list of customers (for customer users who can manage other customers)"""
    admin_id = request.session.get('user_id')
    if not admin_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
        
    try:
        customers = CustomerTable.objects.filter(admin__admin_id=admin_id).order_by('-created_at')
    except Exception:
        messages.error(request, "Error retrieving customer list.")
        return redirect('customer_app:customer_dashboard')
    
    # Add pagination
    paginator = Paginator(customers, 10)  # 10 customers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'superadmin_app/customers_list.html', {'page_obj': page_obj})

@role_required('customer')
def customer_subscribers(request):
    """View customer subscribers"""
    customer_id = request.session.get('user_id')
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login_app:login')
        
    try:
        customer = CustomerTable.objects.get(customer_id=customer_id)
        subscribers = Subscription.objects.filter(
            customer_id=customer,
            subscription_type='customer'
        ).order_by('-start_date')
    except Exception as e:
        messages.error(request, f"Error retrieving subscription data: {str(e)}")
        return redirect('customer_app:customer_dashboard')
    
    # Add pagination
    paginator = Paginator(subscribers, 10)  # 10 subscribers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'customer_app/subscribers.html', {'page_obj': page_obj})

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

@csrf_exempt
def create_partial_payment_order(request):
    """Create a partial payment order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=400)
        
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        order_id = data.get('order_id')
        customer_id = data.get('customer_id')

        
        if not amount or not order_id:
            return JsonResponse({'success': False, 'error': 'Amount and order_id are required'}, status=400)
            
        # Check if Razorpay credentials are available
        if not RAZORPAY_KEY_ID or not RAZORPAY_SECRET:
            return JsonResponse({'success': False, 'error': 'Razorpay credentials not configured'}, status=500)
            
        # Create Razorpay order
        razorpay_data = {
            'amount': int(amount * 100),  # Amount in paise
            'currency': 'INR',
            'receipt': f'partial_{order_id}_{int(time.time())}',
            'payment_capture': 1  # Auto-capture
        }
        
      
        razorpay_order = client.order.create(data=razorpay_data)

        
        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'amount': int(amount * 100),  # Amount in paise for Razorpay
            'key_id': RAZORPAY_KEY_ID
        })
        
    except Exception as e:
     
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

@require_POST
@csrf_exempt
def verify_partial_payment(request):
    """API endpoint to verify and process partial payment for customer orders"""
    try:
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id') # This is Razorpay's order_id
        razorpay_signature = data.get('razorpay_signature')
        
        # Retrieve original order_id and amount from session or request as per your flow
        # Assuming 'order_id' in data refers to your application's Order.order_id
        # And 'amount' is the amount paid in this transaction.
        application_order_id = data.get('order_id') 
        amount_paid_this_transaction = float(data.get('amount'))

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, application_order_id, amount_paid_this_transaction]):
            return JsonResponse({'success': False, 'message': 'Missing payment verification data.'}, status=400)

        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id, # Use Razorpay's order_id for verification
            'razorpay_signature': razorpay_signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        order = get_object_or_404(Orders, order_id=application_order_id)
          # --- Create Payment Record ---
        try:
            Payments.objects.create(
                order=order,
                amount=amount_paid_this_transaction,
                date=timezone.now().date(),
                reference=f"order_{application_order_id}_partial_{razorpay_payment_id}",
                proof_link=razorpay_payment_id,
                payment_method="Razorpay"
            )
        except Exception as e:
            print(f"Error creating payment record for order {application_order_id}: {e}")
            # Decide if this error should halt the process or just be logged
            # For now, we'll let the main process continue but log it.
            messages.warning(request, "Payment successful, but an error occurred while logging payment details.")

        current_paid = order.paid_amount or 0
        order.paid_amount = current_paid + amount_paid_this_transaction
        
        if order.paid_amount >= order.overall_amount:
            order.payment_status = 2  # Fully paid
            payment_status_text = "fully paid"
        else:
            order.payment_status = 1  # Partially paid
            payment_status_text = "partially paid"
        
        order.save()
        
        # Create payment notifications
        create_notification(
            user_type='customer',
            user_id=order.customer.customer_id,
            notification_type='payment_received',
            title='Payment Received',
            message=f'Payment of ₹{amount_paid_this_transaction} received for order #{order.order_id}. Order is now {payment_status_text}.',
            related_order_id=order.order_id
        )
        
        # Notification for admin
        create_notification(
            user_type='admin',
            user_id=order.admin.admin_id,
            notification_type='payment_received',
            title='Customer Payment Received',
            message=f'Payment of ₹{amount_paid_this_transaction} received from {order.customer.first_name} {order.customer.last_name} for order #{order.order_id}. Order is now {payment_status_text}.',
            related_order_id=order.order_id
        )
        
        # Clear relevant session data if you stored any for this transaction
        # Example:
        # if 'partial_payment_razorpay_order_id' in request.session:
        #     del request.session['partial_payment_razorpay_order_id']
        
        messages.success(request, "Payment successful and order updated.") # For display on next page load
        return JsonResponse({'success': True, 'message': 'Payment verified and order updated.'})
        
    except razorpay.errors.SignatureVerificationError as e:
        print(f"Signature Verification Error for order payment: {e}")
        return JsonResponse({'success': False, 'message': 'Payment verification failed: Invalid signature.'}, status=400)
    except Orders.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found.'}, status=404)
    except Exception as e:
        print(f"Error in verify_partial_payment: {e}")
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)