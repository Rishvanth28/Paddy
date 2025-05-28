"""
Views module for Paddy application.

This module contains all the view functions that handle HTTP requests
and return appropriate responses. It includes functionality for user authentication,
dashboard views, customer and admin management, order processing, and payment handling.
"""

import json
import re
import logging
from functools import wraps
from datetime import date, timedelta

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.timezone import now
from django.conf import settings
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from dotenv import load_dotenv
import os

load_dotenv()
# RAZORPAY_KEY_ID=rzp_test_zOexMQY9CNEGzd
# RAZORPAY_SECRET=Gmtv3UfGPIavIeneKQjkZTcu
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))
def login_view(request):
    """
    Handle user login for superadmin, admin, and customer roles.
    
    Validates credentials and redirects to appropriate dashboard based on role.
    Also handles subscription status checks for admin and customer accounts.
    """
    # Check if user is already logged in
    if request.session.get("user_id") and request.session.get("role"):
        # Direct redirect to appropriate dashboard based on role
        role_dashboard_map = {
            "superadmin": "superadmin_dashboard",
            "admin": "admin_dashboard",
            "customer": "customer_dashboard"
        }
        role = request.session["role"]
        if role in role_dashboard_map:
            return redirect(role_dashboard_map[role])
    
    if request.method == "POST":
        # Get form data
        phone_number = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        
        # Validate required fields
        if not all([phone_number, password, role]):
            messages.error(request, "All fields are required.")
            return redirect("login")
        
        # Define valid roles
        valid_roles = ["superadmin", "admin", "customer"]
        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect("login")
            
        try:
            # Handle login based on role
            if role == "superadmin":
                return handle_superadmin_login(request, phone_number, password)
            elif role == "admin":
                return handle_admin_login(request, phone_number, password)
            elif role == "customer":
                return handle_customer_login(request, phone_number, password)
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Login error: {str(e)}")
            messages.error(request, "An error occurred during login. Please try again.")
    
    # Render the login form for GET requests or failed logins
    return render(request, "login.html")

def handle_superadmin_login(request, phone_number, password):
    """Handle superadmin authentication and session creation."""
    try:
        user = AdminTable.objects.get(phone_number=phone_number)
        
        # Check if this admin has superadmin privileges (admin_id == 1000000)
        if user.admin_id > 1000000:
            messages.error(request, "Unauthorized access.")
            return redirect("login")
            
        # Verify password
        if check_password(password, user.password):
            # Set session data
            request.session["user_id"] = user.admin_id
            request.session["role"] = "superadmin"
            return redirect("superadmin_dashboard")
        else:
            messages.error(request, "Invalid credentials.")
    except AdminTable.DoesNotExist:
        messages.error(request, "Super Admin not found.")
    
    return redirect("login")

def handle_admin_login(request, phone_number, password):
    """Handle admin authentication, subscription check, and session creation."""
    try:
        user = AdminTable.objects.get(phone_number=phone_number)
        
        # Prevent superadmin from logging in as admin
        if user.admin_id == 1000000:
            messages.error(request, "Unauthorized access.")
            return redirect("login")
            
        # Verify password
        if check_password(password, user.password):
            # Set session data
            request.session["user_id"] = user.admin_id
            request.session["role"] = "admin"
              # Check subscription status
            current_date = now().date()
            sub = Subscription.objects.filter(
                admin_id=user, 
                subscription_type="admin",
                end_date__gte=current_date,
                payment_amount__gt=0  # Only paid subscriptions are valid for admins
            ).order_by("-end_date").first()
            
            # Redirect based on subscription status
            if sub:
                return redirect("admin_dashboard")
            else:
                messages.info(request, "Please purchase a subscription to continue.")
                return redirect("admin_subscription_payment")
        else:
            messages.error(request, "Invalid credentials.")
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found.")
    
    return redirect("login")

def handle_customer_login(request, phone_number, password):
    """Handle customer authentication, subscription check, and session creation."""
    try:
        user = CustomerTable.objects.get(phone_number=phone_number)
        
        # Verify password
        if check_password(password, user.password):
            # Set session data
            request.session["user_id"] = user.customer_id
            request.session["role"] = "customer"
            
            # Get current date for subscription checks
            current_date = now().date()
            
            # Check if user has an active subscription
            sub = Subscription.objects.filter(
                customer_id=user, 
                subscription_type="customer"
            ).order_by("-end_date").first()
            
            if sub:
                # Check if subscription is active
                if sub.end_date and sub.end_date >= current_date:
                    return redirect("customer_dashboard")
                else:
                    # Subscription expired
                    return redirect("customer_subscription_payment")
            else:
                # No subscription found, create free trial
                with transaction.atomic():
                    Subscription.objects.create(
                        customer_id=user,
                        subscription_type="customer",
                        subscription_status=1,  # Active status
                        payment_amount=0,       # Free trial
                        start_date=current_date,
                        end_date=current_date + timedelta(days=30)  # 30-day trial
                    )
                return redirect("customer_dashboard")
        else:
            messages.error(request, "Invalid credentials.")
    except CustomerTable.DoesNotExist:
        messages.error(request, "Customer not found.")
    
    return redirect("login")

@role_required(["superadmin"])
def superadmin_dashboard(request):
    """Render the superadmin dashboard."""
    return render(request, "superadmin_dashboard.html")

@role_required(["admin"])
def admin_dashboard(request):
    """Render the admin dashboard."""
    return render(request, "admin_dashboard.html")

def upgrade_plan(request):
    """Render the upgrade plan page."""
    return render(request, "upgrade_plan.html")

@role_required(["customer"])
def customer_dashboard(request):
    """Render the customer dashboard."""
    return render(request, "customer_dashboard.html")

def validate_gst(gst):
    """
    Validate GST number format using regex pattern.
    
    Args:
        gst (str): GST number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not gst:
        return False
    
    # Standard GST format: 2 digits, 5 chars, 4 digits, 1 char, 1 char, Z, 1 char
    gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gst_pattern, gst))

@role_required(["superadmin"])
def onboard(request):
    """Render the onboarding page for superadmin."""
    return render(request, "onboard.html")

@role_required(["superadmin"])
def create_admin(request):
    """
    Create a new admin account with basic validation.
    
    This view handles the creation of new admin accounts by superadmins.
    It validates inputs, checks for duplicate email/phone, and creates
    the admin with default user_count = 50.
    """
    if request.method == "POST":
        # Extract form data
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Validate required fields
        if not all([first_name, last_name, phone_number, email, password]):
            messages.error(request, "All fields are required.")
            return redirect("onboard")

        # Check for existing email or phone number
        if AdminTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for an admin!")
            return redirect("onboard")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("onboard")

        try:
            # Create the admin with hashed password
            AdminTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=make_password(password),  # Hash the password
                user_count=50  # Default user count
            )
            messages.success(request, "Admin created successfully!")
            return redirect("onboard")
        except IntegrityError as e:
            logger.error(f"Error creating admin: {str(e)}")
            messages.error(request, "Failed to create admin. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error creating admin: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            
    return render(request, "onboard.html")

@role_required(["superadmin", "admin"])
def create_customer(request):
    """
    Create a new customer account with validation.
    
    This view handles the creation of new customer accounts by both superadmins
    and regular admins. It validates inputs, checks for duplicate email/phone,
    verifies GST format, and creates the customer with a default subscription.
    """
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    if request.method == "POST":
        # Extract form data
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        company_name = request.POST.get("company_name", "").strip()
        gst = request.POST.get("gst", "").strip()
        address = request.POST.get("address", "").strip()

        # Get admin from session
        admin_id = request.session.get("user_id")
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login")

        # Validate required fields
        if not all([first_name, last_name, phone_number, email, password]):
            messages.error(request, "All fields are required.")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        # Check customer limit
        current_customer_count = CustomerTable.objects.filter(admin=admin).count()
        if current_customer_count >= admin.user_count:
            messages.error(request, "Customer limit reached for your account!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        # Check for existing email or phone
        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        # Validate GST if provided
        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        try:
            # Use transaction to ensure both customer and subscription are created or neither
            with transaction.atomic():
                # Create the customer
                customer = CustomerTable.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    email=email,
                    password=make_password(password),  # Hash the password
                    company_name=company_name,
                    GST=gst if gst else None,
                    address=address,
                    admin=admin,
                )

                # Create default 1-month free subscription for customer
                current_date = now().date()
                Subscription.objects.create(
                    customer_id=customer,
                    subscription_type="customer",
                    subscription_status=1,  # Active status
                    payment_amount=0,       # Free trial
                    start_date=current_date,
                    end_date=current_date + timedelta(days=30)  # 30-day trial
                )

            messages.success(request, "Customer created successfully!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        except IntegrityError as e:
            logger.error(f"Error creating customer: {str(e)}")
            messages.error(request, "Failed to create customer. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again.")

    # Render the appropriate template for GET requests
    return render(request, "onboard.html" if is_superadmin else "customer_onboard.html")


@role_required(["superadmin", "admin"])
def place_order(request):
    """
    Handle order placement with payment processing via Razorpay.
    
    This function handles three scenarios:
    1. Initial page load (GET request)
    2. AJAX request to create a Razorpay order for booking fee
    3. Payment verification callback after successful payment
    
    The order flow includes:
    - Collecting order details (regular order or multiple products)
    - Creating a Razorpay order for booking fee
    - Verifying payment and creating the actual order in database
    """
    role = request.session.get("role")
    is_superadmin = role == "superadmin"
    admin_id = request.session.get("user_id")
    
    if not admin_id:
        logger.warning("Unauthorized access attempt to place_order: no admin_id in session")
        return redirect("login")

    # Get customers for the admin to populate dropdown
    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    
    # Handle Razorpay payment verification callback
    if request.method == "POST" and request.POST.get("razorpay_payment_id"):
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")
        temp_data_json = request.session.get("temp_order_data")
        
        if not temp_data_json:
            messages.error(request, "Order data not found. Please try again.")
            return redirect("place_order" if is_superadmin else "admin_place_order")
        
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
            if temp_data["product_category_id"] != "3":
                # Regular order flow
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                gst = customer.GST

    # Calculate amount
    quantity = float(temp_data["quantity"]) if temp_data["quantity"] else 0
    price_per_unit = float(temp_data["price_per_unit"]) if temp_data["price_per_unit"] else 0
    overall_amount = quantity * price_per_unit

    # Create order record
    with transaction.atomic():
        order = Orders.objects.create(
            customer=customer,
            admin=AdminTable.objects.get(admin_id=admin_id),
            payment_status=0,  # Unpaid
            delivery_status=0,  # Not delivered
            product_category_id=temp_data["product_category_id"],
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

def process_multiple_products_order(temp_data, admin_id, payment):
    """
    Process an order with multiple products.
    
    Args:
        temp_data: Dictionary containing order details
        admin_id: The ID of the admin creating the order
        payment: The payment object for booking fee
    """
    customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
    gst = customer.GST
    
    # Create order first
    with transaction.atomic():
        order = Orders.objects.create(
            customer=customer,
            admin=AdminTable.objects.get(admin_id=admin_id),
            payment_status=0,  # Unpaid
            quantity=0,  # Total quantity will be calculated from items
            product_category_id=temp_data["product_category_id"],
            GST=gst,
            lorry_number=temp_data["lorry_number"],
            driver_name=temp_data["driver_name"],
            delivery_date=temp_data["delivery_date"],
            delivery_status=0,  # Not delivered
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
        
        # Create order items efficiently using bulk create
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
                quantity=int(float(quantities[i])) if quantities[i] else 0,
                price_per_unit=float(prices[i]) if prices[i] else 0,
                total_amount=float(totals[i]) if totals[i] else 0,
                unit=units[i]
            )
            order_items.append(item)
        
        # Calculate total amount
        order.overall_amount = sum(float(totals[i]) for i in range(len(totals)) 
                                if totals[i].strip())
        order.save()
        
        # Bulk create all items at once (more efficient than individual creates)
        if order_items:
            OrderItems.objects.bulk_create(order_items)

def create_razorpay_order(request, admin_id):
    """
    Create a Razorpay order for booking fee payment.
    
    Args:
        request: The HTTP request object
        admin_id: The ID of the admin creating the order
        
    Returns:
        JsonResponse: Order details for frontend processing
    """
    # Store order data temporarily
    temp_data = {}
    
    # Process data based on product category
    if str(request.POST.get("product_category_id")) != "3":
        # Regular order
        temp_data = {
            "customer_id": request.POST.get("customer"),
            "product_category_id": request.POST.get("product_category_id"),
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
    except requests.exceptions.ConnectionError as e:
        # Handle connection errors (internet connectivity issues)
        logger.error(f"Connection error with Razorpay API: {str(e)}")
        error_msg = "Unable to connect to payment gateway. Please check your internet connection or contact support."
        return JsonResponse({
            "status": "error",
            "message": error_msg
        })
    except Exception as e:
        logger.error(f"Failed to create Razorpay order: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"Error creating payment: {str(e)}"
        })


@role_required(["customer"])
def customer_orders(request):
    """
    Display orders for the logged-in customer.
    
    Handles both regular page load (HTML view) and AJAX requests (JSON data).
    Uses lazy loading to avoid loading all order data at once.
    """
    customer_id = request.session.get("user_id")
    if not customer_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login')
    
    # Check if it's an AJAX request asking for JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Fetch orders with pagination if needed
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        
        try:
            page = int(page)
            limit = min(int(limit), 50)  # Cap limit to prevent excessive loads
        except (ValueError, TypeError):
            page = 1
            limit = 10
            
        # Calculate offset for database query
        offset = (page - 1) * limit
        
        # Fetch orders with limit and offset for efficient pagination
        orders = Orders.objects.filter(
            customer__customer_id=customer_id
        ).order_by('-order_date')[offset:offset + limit]
        
        # Convert to JSON serializable format with only necessary fields
        orders_data = [{
            'order_id': order.order_id,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
            'overall_amount': float(order.overall_amount) if order.overall_amount else 0,
            'paid_amount': float(order.paid_amount) if order.paid_amount else 0,
            'payment_status': order.payment_status,
            'delivery_status': order.delivery_status,
            'product_category_id': order.product_category_id,
            'product_name': 'Multiple Products' if order.product_category_id == 3 else 
                          'Paddy' if order.product_category_id == 2 else 'Rice'
        } for order in orders]
        
        # Get total count for pagination
        total_orders = Orders.objects.filter(customer__customer_id=customer_id).count()
        
        return JsonResponse({
            'orders': orders_data,
            'total': total_orders,
            'pages': (total_orders + limit - 1) // limit  # Ceiling division
        })
    
    # For regular page load, just render the template (JS will fetch data)
    return render(request, 'customer_order.html')

@role_required(["customer"])
def payment(request):
    """
    Display payment information for a specific order.
    
    Gathers order details, calculates payment status, and prepares
    the data for invoice rendering.
    """
    # Validate input
    order_id = request.POST.get('order_id')
    if not order_id:
        messages.error(request, "Order ID is required.")
        return redirect('customer_orders')
    
    try:
        # Fetch order with related customer data in a single query
        order = Orders.objects.select_related('customer').get(pk=order_id)
    except Orders.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('customer_orders')
        
    # Security check: ensure the order belongs to the logged-in customer
    if order.customer.customer_id != request.session.get("user_id"):
        logger.warning(f"Unauthorized access attempt to order {order_id}")
        messages.error(request, "You don't have permission to access this order.")
        return redirect('customer_orders')
    
    # Fetch order items based on product category
    if order.product_category_id == 3:  # Multiple products
        order_items = list(OrderItems.objects.filter(order=order).values(
            'product_name', 'quantity', 'price_per_unit', 'total_amount'
        ))
    else:  # Single product (Rice or Paddy)
        product_name = 'Paddy' if order.product_category_id == 2 else 'Rice'
        order_items = [{
            'product_name': product_name,
            'quantity': order.quantity,
            'price_per_unit': float(order.price_per_unit) if order.price_per_unit else 0,
            'total_amount': float(order.overall_amount) if order.overall_amount else 0
        }]
    
    # Calculate financial information
    total_amount = float(order.overall_amount) if order.overall_amount else 0
    paid_amount = float(order.paid_amount) if order.paid_amount else 0
    balance_due = total_amount - paid_amount
    
    # Determine payment status
    if paid_amount == 0:
        payment_status = 0  # Pending
    elif paid_amount < total_amount:
        payment_status = 1  # Partially Paid
    else:
        payment_status = 2  # Fully Paid
    
    # Calculate payment deadline date
    payment_deadline = order.order_date + timedelta(days=order.payment_deadline or 30)
    
    # Map product category to readable name
    product_category_names = {
        1: 'Rice',
        2: 'Paddy',
        3: 'Fertilizer'
    }
    order_name = product_category_names.get(order.product_category_id, 'Product')
    
    # Prepare context for template
    context = {
        'order': order,
        'order_name': order_name,
        'order_items': order_items,
        'customer': order.customer,
        'total_amount': total_amount,
        'payment_terms': order.payment_deadline,
        'balance_due': balance_due,
        'payment_status': payment_status,
        'invoice_date': order.order_date,
        'total_items': sum(item['quantity'] for item in order_items),
        'invoice_number': f"UFs {order.order_id}",
        'payment_deadline': payment_deadline,
        'amount_in_words': number_to_words_indian(total_amount),
        'business_year': f"urakadai {order.order_date.year}",
    }
    
    return render(request, 'payment.html', context)

@require_POST
@csrf_exempt
def create_partial_payment_order(request):
    """API endpoint to create a Razorpay order for partial payment"""
    try:
        # Parse request data
        data = json.loads(request.body)
        order_id = data.get('order_id')
        amount = float(data.get('amount', 0))
        
        # Validate required fields
        if not order_id:
            return JsonResponse({
                'success': False, 
                'message': 'Order ID is required'
            })
        
        if amount <= 0:
            return JsonResponse({
                'success': False, 
                'message': 'Amount must be greater than zero'
            })
        
        # Get the order
        try:
            order = Orders.objects.get(order_id=order_id)
        except Orders.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Order not found'
            })
        
        # Validate amount
        paid_amount = order.paid_amount or 0
        balance_due = order.overall_amount - paid_amount
        
        if amount > balance_due:
            return JsonResponse({
                'success': False, 
                'message': f'Amount exceeds balance due (₹{balance_due})'
            })
            
        # Create Razorpay order (amount in paise)
        razorpay_amount = int(amount * 100)
        
        # Add receipt and notes for better tracking
        receipt = f'rcpt_{order_id}_{int(timezone.now().timestamp())}'
        
        order_data = {
            'amount': razorpay_amount,
            'currency': 'INR',
            'receipt': receipt,
            'payment_capture': 1,  # Auto-capture
            'notes': {
                'order_id': order_id,
                'customer_id': order.customer.customer_id,
                'payment_type': 'partial_payment'
            }
        }
        
        try:
            # Create the order in Razorpay
            razorpay_order = client.order.create(data=order_data)
            
            # Store order details in session for verification later
            request.session['partial_payment_order_id'] = razorpay_order['id']
            request.session['partial_payment_amount'] = amount
            request.session['partial_payment_for_order'] = order_id
            
            return JsonResponse({
                'success': True,
                'key_id': RAZORPAY_KEY_ID,
                'amount': razorpay_amount,
                'razorpay_order_id': razorpay_order['id'],
                'currency': 'INR',
                'receipt': receipt
            })
        except requests.exceptions.ConnectionError as e:            # Handle connection errors (internet connectivity issues)
            logger.error(f"Connection error with Razorpay API: {str(e)}")
            error_msg = "Unable to connect to payment gateway. Please check your internet connection or contact support."
            return JsonResponse({
                'success': False,
                'message': error_msg
            })
        
    except ValueError as e:
        logger.error(f"Invalid data format in create_partial_payment_order: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid data format'
        })
    except Exception as e:
        logger.error(f"Error in create_partial_payment_order: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing your request'
        })

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
        else:
            order.payment_status = 1  # Partially paid
        
        order.save()
        
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
        
def customer_delivery_validation(request):
    """
    Handle customer validation of order delivery status.
    
    This allows customers to confirm whether an order has been delivered correctly,
    updating the delivery status accordingly.
    """
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        delivery_status = request.POST.get('delivery_status')
        customer_id = request.session.get('user_id')
        
        # Validate inputs
        if not all([order_id, delivery_status, customer_id]):
            messages.error(request, "Missing required information.")
            return redirect('customer_orders')
            
        try:
            # Convert delivery status to integer and validate range (0-2)
            delivery_status = int(delivery_status)
            if delivery_status not in range(3):  # 0, 1, 2
                messages.error(request, "Invalid delivery status.")
                return redirect('customer_orders')
                
            # Fetch the order with customer check for security
            order = Orders.objects.get(
                order_id=order_id, 
                customer__customer_id=customer_id
            )
            
            # Update and save
            order.delivery_status = delivery_status
            order.save()
            
            status_messages = {
                0: "Order marked as not delivered.",
                1: "Order marked as partially delivered.",
                2: "Order marked as fully delivered."
            }
            
            messages.success(request, status_messages.get(delivery_status, "Delivery status updated."))
            return redirect('customer_orders')
            
        except Orders.DoesNotExist:
            logger.warning(f"Customer {customer_id} attempted to update non-existent or unauthorized order {order_id}")
            messages.error(request, "Order not found or you don't have permission to update it.")
            return redirect('customer_orders')
        except ValueError:
            messages.error(request, "Invalid delivery status value.")
            return redirect('customer_orders')
        except Exception as e:
            logger.error(f"Error in customer_delivery_validation: {str(e)}")
            messages.error(request, "An error occurred while updating delivery status.")
            return redirect('customer_orders')
    
    # If not POST, redirect to orders page
    return redirect('customer_orders')

@role_required(["admin"])
def customer_onboard_view(request):
    """Render the customer onboarding page for admins."""
    return render(request, "customer_onboard.html")

@role_required(["admin"])
def admin_add_subscription(request):
    """
    Handle admin requests to increase their user count subscription.
    
    This function allows admins to request more user slots by creating a 
    UserIncreaseSubscription record that will be reviewed by a superadmin.
    """
    # Get current admin info
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
                messages.warning(request, "You already have an active subscription upgrade request.")
            else:
                try:
                    UserIncreaseSubscription.objects.create(
                        admin_id=admin,
                        subscription_status=0 # Status 0: Pending Superadmin Approval
                    )
                    messages.success(request, "Subscription upgrade request submitted successfully! It will be reviewed by the superadmin.")
                except Exception as e:
                    messages.error(request, f"Failed to submit subscription request. Error: {str(e)}")
            return redirect('admin_add_subscription') # Redirect to show messages and prevent re-submission

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

@require_POST # Ensures this view only accepts POST requests
@role_required(["admin"]) # Protect the endpoint
# @csrf_exempt # Not needed if CSRF token is handled correctly with AJAX from same domain
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
        request.session['user_increase_sub_id'] = subscription.sid
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
        subscription.save()

        # Increase admin's user count
        admin_user.user_count += 50 # Or whatever the agreed increase is
        admin_user.save()

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


@role_required(["superadmin"])
def superadmin_subscription(request):
    """
    Display and filter admin subscription requests for superadmins.
    
    This view allows superadmins to see all subscription increase requests
    and filter them by status (pending, approved, rejected).
    """
    # Get filter parameters with validation
    try:
        status_filter = int(request.GET.get('status', '')) if request.GET.get('status', '') != '' else ''
    except ValueError:
        status_filter = ''
      # Base queryset with prefetched admin data to reduce DB queries
    subscriptions_queryset = UserIncreaseSubscription.objects.select_related('admin_id').order_by('-start_date')
    
    # Apply status filter if provided (0=pending, 1=approved, 2=rejected)
    if status_filter != '':
        subscriptions_queryset = subscriptions_queryset.filter(subscription_status=status_filter)
    
    # Pagination with error handling
    try:
        page_size = 10  # Items per page
        paginator = Paginator(subscriptions_queryset, page_size)
        page_number = max(1, int(request.GET.get('page', 1)))  # Ensure page is at least 1
        page_number = min(page_number, paginator.num_pages)  # Ensure page doesn't exceed max
        subscriptions = paginator.get_page(page_number)
    except (ValueError, TypeError):
        # Handle invalid page number
        subscriptions = paginator.get_page(1)
      # Count by status for summary stats
    status_counts = {
        'total': subscriptions_queryset.count(),
        'pending': subscriptions_queryset.filter(subscription_status=0).count(),
        'approved': subscriptions_queryset.filter(subscription_status=1).count(),
        'rejected': subscriptions_queryset.filter(subscription_status=2).count(),
    }
    
    context = {
        'subscriptions': subscriptions,
        'status_filter': status_filter,
        'status_counts': status_counts,
    }
    
    return render(request, "superadmin_subscription.html", context)

@role_required(["superadmin"])
def superadmin_subscription_review(request):
    """
    Handle the review and approval/rejection of admin subscription requests.
    
    This function processes form submissions to update subscription status
    and increase admin user counts when approved.
    """
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription_id')
        subscription_status = request.POST.get('subscription_status')
        payment_amount = request.POST.get('payment_amount', '0')
        
        # Input validation
        if not all([subscription_id, subscription_status]):
            messages.error(request, "Missing required information.")
            return redirect('superadmin_subscription')
            
        try:
            # Validate numeric inputs
            subscription_id = int(subscription_id)
            subscription_status = int(subscription_status)
            payment_amount = float(payment_amount)
            
            # Status should be either 1 (approved) or 2 (rejected)
            if subscription_status not in [1, 2]:
                messages.error(request, "Invalid subscription status.")
                return redirect('superadmin_subscription')
                
            # Get the subscription record
            with transaction.atomic():
                subscription = UserIncreaseSubscription.objects.select_related('admin_id').get(sid=subscription_id)
                
                # Can only review pending subscriptions
                if subscription.subscription_status != 0:
                    messages.warning(request, "This subscription request has already been processed.")
                    return redirect('superadmin_subscription')
                  # Update subscription status
                subscription.subscription_status = subscription_status
                # We don't have a reviewed_at field, so we'll just update the end_date if it's not set
                if not subscription.end_date:
                    subscription.end_date = timezone.now().date() + timedelta(days=30)
                
                if subscription_status == 1:  # Approved
                    # Update payment amount
                    subscription.payment_amount = payment_amount
                    
                    # Increase user count for the admin
                    admin = subscription.admin_id
                    admin.user_count += subscription.requested_user_count
                    admin.save()
                    
                    messages.success(
                        request, 
                        f"Subscription request #{subscription_id} approved. "
                        f"Admin {admin.first_name} {admin.last_name} now has {admin.user_count} user slots."
                    )
                else:  # Rejected
                    messages.info(request, f"Subscription request #{subscription_id} has been rejected.")
                
                subscription.save()
                
        except UserIncreaseSubscription.DoesNotExist:
            messages.error(request, "Subscription request not found.")
        except ValueError:
            messages.error(request, "Invalid input values.")
        except Exception as e:
            logger.error(f"Error in superadmin_subscription_review: {str(e)}")
            messages.error(request, "An error occurred while processing the subscription.")
    
    # Always redirect to the subscription list
    return redirect('superadmin_subscription')

@role_required(["customer"])
def upgrade_to_admin(request):
    """
    Handle customer requests to upgrade to admin status.
    
    This function creates a new admin account for an existing customer
    while maintaining their same login credentials.
    """
    customer_id = request.session.get('user_id')
    
    try:
        # Get customer data
        customer = CustomerTable.objects.get(customer_id=customer_id)
        
        # Check if already an admin
        if AdminTable.objects.filter(email=customer.email).exists():
            messages.info(request, "You already have an admin account with this email.")
            return render(request, 'upgrade_to_admin.html', {'customer': customer})
            
        if request.method == 'POST':
            try:                # Use transaction to ensure consistency
                with transaction.atomic():
                    # Create new admin with same credentials
                    new_admin = AdminTable(
                        first_name=customer.first_name,
                        last_name=customer.last_name,
                        phone_number=customer.phone_number,
                        email=customer.email,
                        password=customer.password,  # Already hashed from customer account
                        user_count=5  # Start with a small number of user slots
                    )
                    new_admin.save()
                    
                # Store admin ID in session for subscription payment
                request.session["user_id"] = new_admin.admin_id
                request.session["role"] = "admin"
                
                messages.success(request, "Successfully created admin account! Please purchase a subscription to continue.")
                return redirect('admin_subscription_payment')
                
            except IntegrityError:
                messages.error(request, "An error occurred during upgrade. This email or phone may already be registered as an admin.")
            except Exception as e:
                logger.error(f"Error in upgrade_to_admin: {str(e)}")
                messages.error(request, "An unexpected error occurred. Please try again later.")
        
        # For GET requests or after handling POST
        return render(request, 'upgrade_to_admin.html', {'customer': customer})
        
    except CustomerTable.DoesNotExist:
        logger.error(f"Customer not found in upgrade_to_admin: {customer_id}")
        messages.error(request, "Customer account not found. Please log in again.")
        return redirect('login')

        messages.success(request, "You have been upgraded to admin successfully!")
        return render(request, 'upgrade_to_admin.html', {'customer': customer})

    return render(request, 'upgrade_to_admin.html', {'customer': customer})

@role_required(["admin"])
def upgrade_to_customer(request):
    """
    Allow an admin to create a linked customer account.
    
    This enables the admin to also have a customer role with its own
    dashboard and permissions. The accounts are linked by phone number
    and email for seamless role switching.
    """
    try:
        # Get current admin info
        admin_id = request.session.get('user_id')
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect('login')
            
        admin = get_object_or_404(AdminTable, admin_id=admin_id)
        
        # Check if already a customer
        if CustomerTable.objects.filter(email=admin.email).exists():
            messages.info(request, "You already have a customer account. Use the role switcher to access it.")
            return redirect('admin_dashboard')
            
        if request.method == 'POST':
            # Extract form data
            company_name = request.POST.get('company_name', '').strip()
            gst = request.POST.get('GST', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Validate required fields
            if not all([company_name, address]):
                messages.error(request, "Company name and address are required.")
                return render(request, 'upgrade_to_customer.html', {'admin': admin})
                
            # Validate GST if provided
            if gst and not validate_gst(gst):
                messages.error(request, "Invalid GST format. Please provide a valid GST number.")
                return render(request, 'upgrade_to_customer.html', {'admin': admin})
                
            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Create new customer account
                new_customer = CustomerTable(
                    admin_id=admin.admin_id,  # Link to admin account
                    first_name=admin.first_name,
                    last_name=admin.last_name,
                    phone_number=admin.phone_number,
                    email=admin.email,
                    password=admin.password,  # Already hashed from admin account
                    company_name=company_name,
                    GST=gst,
                    address=address,
                )
                new_customer.save()
                
                # Create free trial subscription for the new customer
                current_date = timezone.now().date()
                Subscription.objects.create(
                    customer_id=new_customer,
                    subscription_type="customer",
                    subscription_status=1,  # Active
                    payment_amount=0,  # Free trial
                    start_date=current_date,
                    end_date=current_date + timedelta(days=30)  # 30-day trial
                )
            
            messages.success(request, "You have been successfully upgraded to customer!")
            return redirect('upgrade_success')
        
        # Render the upgrade form for GET requests
        return render(request, 'upgrade_to_customer.html', {'admin': admin})
        
    except Exception as e:
        logger.error(f"Error in upgrade_to_customer: {str(e)}")
        messages.error(request, "An error occurred while processing your request.")
        return redirect('admin_dashboard')

def upgrade_success(request):
    return render(request, 'upgrade_success.html')

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')

@role_required(["superadmin"])
def view_admins(request):
    """
    Display a list of admin accounts for the superadmin.
    
    Provides search functionality and pagination.
    Excludes the main superadmin account (admin_id=1000000).
    """
    try:
        # Get search query if any
        query = request.GET.get('q', '')
        
        # Get page number for pagination
        page = request.GET.get('page', 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
            
        # Get admin list, excluding the superadmin
        admins = AdminTable.objects.exclude(admin_id=1000000)
        
        # Apply search filter if a query was provided
        if query:
            admins = admins.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone_number__icontains=query)
            )
            
        # Count active subscriptions for each admin
        admins = admins.annotate(
            active_subscriptions=Count(
                'subscription',
                filter=Q(
                    subscription__subscription_type='admin',
                    subscription__end_date__gte=timezone.now().date()
                )
            )
        )
            
        # Paginate results
        paginator = Paginator(admins, 10)  # 10 admins per page
        try:
            admins_page = paginator.page(page)
        except Exception:
            admins_page = paginator.page(1)
            
        # Prepare context for template
        context = {
            'admins': admins_page,
            'query': query,
            'total_count': paginator.count,
        }
        
        return render(request, 'view_admins.html', context)
        
    except Exception as e:
        logger.error(f"Error in view_admins: {str(e)}")
        messages.error(request, "An error occurred while retrieving admin list.")
        return redirect("superadmin_dashboard")

@role_required(["superadmin"])
def delete_admin(request, admin_id):
    if request.method == "POST":
        admin = get_object_or_404(AdminTable, admin_id=admin_id)

        # Prevent deletion of primary superadmin
        if admin.admin_id == 1000000:
            messages.error(request, "Superadmin cannot be deleted.")
            return redirect("view_admins")

        admin.delete()
        messages.success(request, f"Admin {admin.first_name} {admin.last_name} deleted successfully.")
        return redirect("view_admins")
    else:
        messages.error(request, "Invalid request method.")
        return redirect("view_admins")

@role_required(["superadmin", "admin"])
def view_customers_under_admin(request, admin_id):
    try:
        admin = AdminTable.objects.get(admin_id=admin_id)
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('view_admins')

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    return render(request, 'admin_customers.html', {
        'admin': admin,
        'customers': customers
    })

@role_required(["superadmin", "admin"])
def delete_customer(request, customer_id):
    if request.method == "POST":
        try:
            customer = CustomerTable.objects.get(customer_id=customer_id)
            customer.delete()
            messages.success(request, "Customer deleted successfully.")
        except CustomerTable.DoesNotExist:
            messages.error(request, "Customer not found.")
    return redirect(request.META.get("HTTP_REFERER", "view_admins"))
    
def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login")

@role_required(["superadmin", "admin"])
def customers_under_admin(request):
    admin_id = request.session.get("user_id")  # session must store admin_id during login
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"
    if not admin_id:
        return redirect('admin_login')  # redirect if not logged in

    # Fetch customers for the current admin
    customers = CustomerTable.objects.filter(admin_id=admin_id)

    return render(request, "customers_list.html" if is_superadmin else "admin_customer_list.html", {"customers": customers})

def admin_login_submit(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            admin = AdminTable.objects.get(email=email)
            if admin.check_password(password):
                request.session['user_id'] = admin.admin_id
                return redirect('customers_under_admin')
        except AdminTable.DoesNotExist:
            pass
    return render(request, 'login.html', {'error': 'Invalid credentials'})

def demo(request):
    return render(request, 'demo.html')

def admin_subscription_payment(request):
    if request.method == "POST":
        plan = request.POST.get("plan")
        admin_id = request.session.get("user_id")

        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        amount = 200 if plan == "1month" else 350
        duration = 30 if plan == "1month" else 60

        order_data = {
            "amount": amount * 100,  # In paise
            "receipt": str(int(timezone.now().timestamp())),
            "currency": "INR",
            "payment_capture": "1"
        }

        try:
            razorpay_order = client.order.create(data=order_data)
            
            # Save session details
            request.session["subscription_amount"] = amount
            request.session["subscription_days"] = duration
            request.session["razorpay_order_id"] = razorpay_order["id"]
            request.session["subscription_type"] = "admin"
            request.session["subscription_for"] = "admin"
            request.session["admin_id"] = admin_id
    
            return render(request, "admin_subscription_payment.html", {
                "order_id": razorpay_order["id"],
                "amount": amount * 100,
                "key_id": RAZORPAY_KEY_ID
            })
        except requests.exceptions.ConnectionError as e:
            # Handle connection errors (internet connectivity issues)
            logger.error(f"Connection error with Razorpay API: {str(e)}")
            messages.error(
                request, 
                "Unable to connect to payment gateway. Please check your internet connection or try again later."
            )
            return redirect("admin_dashboard")
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            messages.error(request, f"Error creating payment: {str(e)}")
            return redirect("admin_dashboard")
    
    return render(request, "admin_select_subscription_plan.html")

def customer_subscription_payment(request):
    if request.method == "POST":
        plan = request.POST.get("plan")
        customer_id = request.session.get("user_id")

        if not customer_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        amount = 100 if plan == "1month" else 180
        duration = 30 if plan == "1month" else 60
        
        order_data = {
            "amount": amount * 100,  # In paise
            "receipt": str(int(timezone.now().timestamp())),
            "currency": "INR",
            "payment_capture": "1"
        }

        try:
            razorpay_order = client.order.create(data=order_data)
            
            # Save session details
            request.session["subscription_amount"] = amount
            request.session["subscription_days"] = duration
            request.session["razorpay_order_id"] = razorpay_order["id"]
            request.session["subscription_type"] = "customer"
            request.session["subscription_for"] = "customer"
            request.session["admin_id"] = customer_id
    
            return render(request, "customer_subscription_payment.html", {
                "order_id": razorpay_order["id"],
                "amount": amount * 100,
                "key_id": RAZORPAY_KEY_ID
            })
        except requests.exceptions.ConnectionError as e:
            # Handle connection errors (internet connectivity issues)
            logger.error(f"Connection error with Razorpay API: {str(e)}")
            messages.error(
                request, 
                "Unable to connect to payment gateway. Please check your internet connection or try again later."
            )
            return redirect("customer_dashboard")
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            messages.error(request, f"Error creating payment: {str(e)}")
            return redirect("customer_dashboard")

    return render(request, "customer_select_subscription_plan.html")

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

@csrf_exempt
def payment_success(request):
    """
    Handles successful admin subscription payments.
    Assumes client-side has confirmed Razorpay success and sends details.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # IMPORTANT: Expecting razorpay_payment_id from the client's AJAX call
            razorpay_payment_id = data.get('razorpay_payment_id', 'N/A')

            admin_user_id = request.session.get("user_id") # Assuming user_id is admin_id for this session
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")
            # session_razorpay_order_id = request.session.get("razorpay_order_id") # Razorpay's order ID from session


            if not all([admin_user_id, amount, days]):
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            admin_instance = get_object_or_404(AdminTable, admin_id=admin_user_id)

            # --- Create Payment Record ---
            try:
                Payments.objects.create(
                    order=None, # No direct order for subscriptions
                    amount=float(amount),
                    date=timezone.now().date(),
                    reference=f"admin_sub_{admin_user_id}_{razorpay_payment_id}",
                    proof_link=razorpay_payment_id,
                    payment_method="Razorpay", 
                )
            except Exception as e:
                print(f"Error creating payment record for admin subscription {admin_user_id}: {e}")
                # Log and continue, or handle as critical error

            existing_subscription = Subscription.objects.filter(
                admin_id=admin_instance, # Use instance here
                subscription_type="admin"
            ).order_by("-end_date").first()

            if existing_subscription:
                start_date = existing_subscription.end_date + timedelta(days=1) if existing_subscription.end_date and existing_subscription.end_date >= now().date() else now().date()
                existing_subscription.start_date = start_date
                existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1) # Inclusive end date
                existing_subscription.payment_amount += float(amount)
                existing_subscription.subscription_status = 1 # Active
                existing_subscription.save()
                message_text = "Subscription extended successfully."
            else:
                Subscription.objects.create(
                    admin_id=admin_instance, # Use instance here
                    subscription_type="admin",
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

        except AdminTable.DoesNotExist:
            return JsonResponse({"success": False, "message": "Admin user not found."})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"Error processing admin subscription: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})

@role_required(["admin", "customer"])
def swap_role(request):
    """
    Switch between admin and customer accounts.
    
    This function allows users who have both admin and customer accounts
    (linked by phone number) to switch between roles without logging out.
    The function validates that the linked account exists and is active
    before switching roles.
    """
    try:
        # Get current session info
        current_role = request.session.get("role")
        user_id = request.session.get("user_id")
        
        if not current_role or not user_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")
            
        # Switch from admin to customer
        if current_role == "admin":
            try:
                # Get the admin and find linked customer account
                admin = get_object_or_404(AdminTable, admin_id=user_id)
                customer = get_object_or_404(CustomerTable, phone_number=admin.phone_number)
                
                # Check if customer has active subscription
                current_date = timezone.now().date()
                has_active_subscription = Subscription.objects.filter(
                    customer_id=customer,
                    subscription_type="customer",
                    end_date__gte=current_date
                ).exists()
                
                if not has_active_subscription:
                    messages.warning(request, "Your customer account subscription has expired. Please renew your subscription.")
                    return redirect("admin_dashboard")
                
                # Log the role swap
                logger.info(f"User {admin.email} swapped from admin to customer role")
                
                # Clear session and set new role
                request.session.flush()
                request.session["user_id"] = customer.customer_id
                request.session["role"] = "customer"
                messages.success(request, "Switched to Customer account successfully.")
                return redirect("customer_dashboard")
                
            except CustomerTable.DoesNotExist:
                messages.warning(request, "You don't have a Customer account linked. Please upgrade to customer first.")
                return redirect("admin_dashboard")
        
        # Switch from customer to admin
        elif current_role == "customer":
            try:
                # Get the customer and find linked admin account
                customer = get_object_or_404(CustomerTable, customer_id=user_id)
                admin = get_object_or_404(AdminTable, phone_number=customer.phone_number)
                
                # Check if admin has active subscription
                current_date = timezone.now().date()
                has_active_subscription = Subscription.objects.filter(
                    admin_id=admin,
                    subscription_type="admin",
                    end_date__gte=current_date
                ).exists()
                
                if not has_active_subscription:
                    messages.warning(request, "Your admin account subscription has expired. Please renew your subscription.")
                    return redirect("customer_dashboard")
                
                # Log the role swap
                logger.info(f"User {customer.email} swapped from customer to admin role")
                
                # Clear session and set new role
                request.session.flush()
                request.session["user_id"] = admin.admin_id
                request.session["role"] = "admin"
                messages.success(request, "Switched to Admin account successfully.")
                return redirect("admin_dashboard")
                
            except AdminTable.DoesNotExist:
                messages.warning(request, "You don't have an Admin account linked. Please contact support.")
                return redirect("customer_dashboard")
        
        # Invalid role in session
        else:
            messages.error(request, "Invalid role. Please log in again.")
            return redirect("login")
            
    except Exception as e:
        logger.error(f"Error in swap_role: {str(e)}")
        messages.error(request, "An error occurred while switching roles. Please try again.")
        return redirect("login")

def view_admin_subscribers(request):
    admin_subscriptions = Subscription.objects.filter(subscription_type="admin") \
                                              .select_related('admin_id') \
                                              .order_by('-start_date')
    return render(request, "admin_subscribers.html", {
        "subscriptions": admin_subscriptions,
        "user_type": "admin",  # Make sure to pass this context
    })


def view_customer_subscribers(request):
    customer_subscriptions = Subscription.objects.filter(subscription_type="customer") \
                                                 .select_related('customer_id') \
                                                 .order_by('-start_date')
    
    return render(request, "customer_subscribers.html", {
        "subscriptions": customer_subscriptions,
        "user_type": "customer",  # Added for dynamic display in HTML
    })