from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
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
from django.db.models.functions import ExtractMonth, ExtractYear
import xlsxwriter
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus.flowables import HRFlowable  


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))
def login_view(request):
    if request.session.get("user_id") and request.session.get("role"):
        role = request.session["role"]
        if role == "superadmin":
            return redirect("superadmin_dashboard")
        elif role == "admin":
            return redirect("admin_dashboard")
        elif role == "customer":
            return redirect("customer_dashboard")

    if request.method == "POST":
        phone_number = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        if not phone_number or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("login")

        if role == "superadmin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id > 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "superadmin"
                    return redirect("superadmin_dashboard")
            except AdminTable.DoesNotExist:
                messages.error(request, "Super Admin not found.")

        elif role == "admin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id == 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "admin"
                    sub = Subscription.objects.filter(admin_id=user, subscription_type="admin").order_by("-end_date").first()
                    if sub and sub.end_date and sub.end_date >= now().date():
                        return redirect("admin_dashboard")
                    else:
                        return redirect("admin_subscription_payment")
            except AdminTable.DoesNotExist:
                messages.error(request, "Admin not found.")

        elif role == "customer":
            try:
                user = CustomerTable.objects.get(phone_number=phone_number)
                if check_password(password, user.password):
                    request.session["user_id"] = user.customer_id
                    request.session["role"] = "customer"

                    # Subscription check
                    sub = Subscription.objects.filter(customer_id=user, subscription_type="customer").order_by("-end_date").first()
                    
                    if sub:
                        if sub.end_date and sub.end_date >= now().date():
                            return redirect("customer_dashboard")
                        else:
                            return redirect("customer_subscription_payment")
                    else:
                        # Free trial logic
                        Subscription.objects.create(
                            customer_id=user,
                            subscription_type="customer",
                            subscription_status=1,
                            payment_amount=0,
                            start_date=now().date(),
                            end_date=now().date() + timedelta(days=30)
                        )
                        return redirect("customer_dashboard")
            except CustomerTable.DoesNotExist:
                messages.error(request, "Customer not found.")

        else:
            messages.error(request, "Invalid role selected.")

    return render(request, "login.html")   

@role_required(["superadmin"])
def superadmin_dashboard(request):
    return render(request, "superadmin_dashboard.html")

@role_required(["admin"])
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

def upgrade_plan(request):
    return render(request, "upgrade_plan.html")

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, "customer_dashboard.html")

def validate_gst(gst):
    gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gst_pattern, gst))

@role_required(["superadmin"])
def onboard(request):
    return render(request, "onboard.html")

@role_required(["superadmin"])
def create_admin(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check for existing email or phone number
        if AdminTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for an admin!")
            return redirect("onboard")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("onboard")

        try:
            AdminTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=password,
                user_count=50
            )
            messages.success(request, "Admin created successfully!")
            return redirect("onboard")
        except IntegrityError:
            messages.error(request, "Failed to create admin. Please try again.")
            messages.warning(request, "This email is already registered.")
            messages.info(request, "Please fill all required fields.")
            
    return render(request, "onboard.html")

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
            return redirect("login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login")

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
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

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

            # ✅ Create default 1-month free subscription for customer
            Subscription.objects.create(
                customer_id=customer,
                subscription_type="customer",
                subscription_status=1,
                payment_amount=0,
                start_date=now().date(),
                end_date=now().date() + timedelta(days=30)
            )

            messages.success(request, "Customer created successfully!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "onboard.html" if is_superadmin else "customer_onboard.html")


def create_admin_signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check for existing email or phone number
        if AdminTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for an admin!")
            return redirect("login")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("login")

        try:
            AdminTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=password,
                user_count=50
            )
            messages.success(request, "Admin created successfully!")
            return redirect("login")
        except IntegrityError:
            messages.error(request, "Failed to create admin. Please try again.")
            messages.warning(request, "This email is already registered.")
            messages.info(request, "Please fill all required fields.")
            
    return render(request, "login.html")


def create_customer_signup(request):
    # role = request.session.get("role")
    # is_superadmin = role == "superadmin"

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        gst = request.POST.get("gst")
        address = request.POST.get("address")

        admin_id = 1000000
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login")

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
            return redirect("login")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("login")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("login")

        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("login")

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

            # ✅ Create default 1-month free subscription for customer
            Subscription.objects.create(
                customer_id=customer,
                subscription_type="customer",
                subscription_status=1,
                payment_amount=0,
                start_date=now().date(),
                end_date=now().date() + timedelta(days=30)
            )

            messages.success(request, "Customer created successfully!")
            return redirect("login")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "login.html")


@role_required(["superadmin", "admin"])
def place_order(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login")

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
                
            return redirect("place_order" if is_superadmin else "admin_place_order")
            
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect("place_order" if is_superadmin else "admin_place_order")    # Handle AJAX request for creating Razorpay order
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
    
    # Render the initial form
    return render(request, "place_order.html" if is_superadmin else "admin_place_order.html", {"customers": customers})

@role_required(["customer"])
def customer_orders(request):
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login')
    
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
    return render(request, 'customer_order.html')

@role_required(["customer"])
def payment(request):
    id = request.POST.get('order_id')
    order = Orders.objects.get(pk=id)
    # Assuming you have a related model for order items/products
    # If not, you'll need to create one to store multiple products per order
    if order.product_category_id == 3:
        order_items = OrderItems.objects.filter(order=order)
        order_items = [{'quantity':item.quantity,'price_per_unit':item.price_per_unit,
                        'total_amount':item.total_amount,'product_name':item.product_name} for item in order_items]
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
    return render(request, 'payment.html',context)

@require_POST
@csrf_exempt
def create_partial_payment_order(request):
    """API endpoint to create a Razorpay order for partial payment"""

    
    try:

        data = json.loads(request.body)
        order_id = data.get('order_id')
        amount = float(data.get('amount'))
        
        # Get the order
        order = get_object_or_404(Orders, order_id=order_id)

        
        # Validate amount
        paid_amount = order.paid_amount or 0
        balance_due = order.overall_amount - paid_amount
        
        if amount <= 0 or amount > balance_due:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid payment amount'
            })
        # Create Razorpay order (amount in paise)
        razorpay_amount = int(amount * 100)
        order_data = {
            'amount': razorpay_amount,
            'currency': 'INR',
            'receipt': f'receipt_{order_id}_{timezone.now().timestamp()}',
            'payment_capture': "1",  
            'notes': {
                'order_id': order_id
            }
        }

        
        razorpay_order = client.order.create(data=order_data)
        
        # Store order details in session
        request.session['partial_payment_order_id'] = razorpay_order['id']
        request.session['partial_payment_amount'] = amount
        request.session['partial_payment_for_order'] = order_id
        
        return JsonResponse({
            'success': True,
            'key_id': RAZORPAY_KEY_ID,
            'amount': razorpay_amount,
            'razorpay_order_id': razorpay_order['id']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
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
            return redirect('customer_orders')
        except Orders.DoesNotExist:
            return redirect('customer_orders')

@role_required(["admin"])
def customer_onboard_view(request):
    return render(request, "customer_onboard.html")

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
                messages.warning(request, "You already have an active subscription upgrade request.")
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
        request.session['user_increase_sub_id'] = razorpay_order['id']
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


@role_required(["superadmin"])
def superadmin_subscription(request):
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
    
    return render(request, 'superadmin_subscription.html', context)

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
        
        return redirect('superadmin_subscription')
    
    # If not POST, redirect to the list view
    return redirect('superadmin_subscription')

@role_required(["superadmin"])
def super_admin_orders(request):
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

        # Apply sorting
        orders_query = orders_query.order_by(sort_by)

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
            })
        return JsonResponse({'orders': orders_data})

    return render(request, "superadmin_orders.html")

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

        # Apply sorting
        orders_query = orders_query.order_by(sort_by)

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
            })
        return JsonResponse({'orders': orders_data})

    return render(request, "admin_orders.html")

@role_required(["customer"])
def upgrade_to_admin(request):
    customer_id = request.session.get('user_id')
    customer = CustomerTable.objects.get(customer_id=customer_id)

    # Check if already admin
    if AdminTable.objects.filter(email=customer.email).exists():
        messages.info(request, "You are already an admin! Access denied.")
        return render(request, 'upgrade_to_admin.html', {'customer': customer})

    if request.method == 'POST':
        # Create new admin
        new_admin = AdminTable(
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone_number=customer.phone_number,
            email=customer.email,
            password=customer.password,  # already hashed
            user_count=0,
        )
        new_admin.save()

        messages.success(request, "You have been upgraded to admin successfully!")
        return render(request, 'upgrade_to_admin.html', {'customer': customer})

    return render(request, 'upgrade_to_admin.html', {'customer': customer})

@role_required(["admin"])
def upgrade_to_customer(request):
    admin_id = request.session.get('user_id')
    admin = AdminTable.objects.get(admin_id=admin_id)

    if request.method == 'POST':
        if CustomerTable.objects.filter(email=admin.email).exists():
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

        messages.success(request, "You have been upgraded to customer!")
        return redirect('upgrade_success')

    return render(request, 'upgrade_to_customer.html', {'admin': admin})

def upgrade_success(request):
    return render(request, 'upgrade_success.html')

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')

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

    return render(request, 'view_admins.html', {'admins': admins})

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

def profile(request):
    role = request.session.get('role', 'superadmin')
    if role == 'superadmin':
        base_template = 'superadmin_base.html'
    elif role == 'admin':
        base_template = 'admin_base.html'
    elif role == 'customer':
        base_template = 'customer_base.html'
    else:
        base_template = 'superadmin_base.html'
    context = {
        'base_template': base_template,
    }
    return render(request, 'profile.html', context)

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
            "currency": "INR",
            "payment_capture": "1"
        }

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
            "currency": "INR",
            "payment_capture": "1"
        }

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
                existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1) # Inclusive end date                existing_subscription.payment_amount += float(amount)
                existing_subscription.subscription_status = 1 # Active
                existing_subscription.save()
                message_text = "Subscription extended successfully."
                
                # Create notifications for subscription extension
                create_notification(
                    user_type='admin',
                    user_id=admin_user_id,
                    notification_type='subscription_payment',
                    title='Subscription Extended',
                    message=f'Your subscription has been extended successfully. Payment of ₹{amount} received.',
                    related_subscription_id=existing_subscription.sid
                )
                
                # Notification for superadmin
                create_notification(
                    user_type='superadmin',
                    user_id='1000000',  # Super admin ID
                    notification_type='admin_payment',
                    title='Admin Subscription Payment',
                    message=f'Admin {admin_instance.first_name} {admin_instance.last_name} made subscription payment of ₹{amount}',
                    related_subscription_id=existing_subscription.sid                )
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
                
                # Create notifications for new subscription
                create_notification(
                    user_type='admin',
                    user_id=admin_user_id,
                    notification_type='subscription_payment',
                    title='Subscription Activated',
                    message=f'Your subscription has been activated successfully. Payment of ₹{amount} received.',
                )
                
                # Notification for superadmin
                create_notification(
                    user_type='superadmin',
                    user_id='1000000',  # Super admin ID
                    notification_type='admin_payment',
                    title='New Admin Subscription',
                    message=f'Admin {admin_instance.first_name} {admin_instance.last_name} activated subscription with payment of ₹{amount}',
                )

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

@role_required(["customer"])
def customer_notifications(request):
    """Display notifications for customer"""
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login')
    
    notifications = get_user_notifications('customer', customer_id)
    unread_count = get_unread_notification_count('customer', customer_id)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'customer_notifications.html', context)


@role_required(["admin"])
def admin_notifications(request):
    """Display notifications for admin"""
    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect('login')
    
   
    
    notifications = get_user_notifications('admin', admin_id)
    unread_count = get_unread_notification_count('admin', admin_id)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'admin_notifications.html', context)


@role_required(["superadmin"])
def superadmin_notifications(request):
    """Display notifications for superadmin"""
    admin_id = request.session.get
    
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
    return render(request, 'superadmin_notifications.html', context)


@require_POST
def mark_notification_read(request):
    """Mark a notification as read via AJAX"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if mark_notification_as_read(notification_id):
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    try:
        user_id = request.session.get("user_id")
        role = request.session.get("role")
        
        if not user_id or not role:
            return JsonResponse({'success': False, 'message': 'Session expired'})
        
        user_type = 'superadmin' if role == 'superadmin' else role
        
        Notification.objects.filter(
            user_type=user_type,
            user_id=str(user_id),
            is_read=False
        ).update(is_read=True)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def delete_notifications(request):
    """Delete selected notifications for current user"""
    try:
        # Parse request data
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])
        
        # Validate session
        user_id = request.session.get("user_id")
        role = request.session.get("role")
        
        if not user_id or not role:
            return JsonResponse({'success': False, 'error': 'Session expired'})
        
        if not notification_ids:
            return JsonResponse({'success': False, 'error': 'No notifications selected'})
        
        # Validate notification IDs
        if not isinstance(notification_ids, list):
            return JsonResponse({'success': False, 'error': 'Invalid notification IDs format'})
        
        # Determine user type
        user_type = 'superadmin' if role == 'superadmin' else role
        
        # Delete notifications that belong to the current user
        deleted_count = Notification.objects.filter(
            notification_id__in=notification_ids,
            user_type=user_type,
            user_id=str(user_id)
        ).delete()[0]
        
        if deleted_count > 0:
            return JsonResponse({
                'success': True, 
                'message': f'{deleted_count} notification(s) deleted successfully',
                'deleted_count': deleted_count
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'No notifications found or unauthorized access'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

@role_required(["admin"])
def unified_report_admin(request):
    admin_id = request.session.get("user_id")
    
    # Initialize filters from request parameters
    customer_filter = request.GET.get('customer', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_status = request.GET.get('payment_status', '')
    category_filter = request.GET.get('category', '')
    
    # Base queryset
    orders = Orders.objects.select_related('customer', 'admin').prefetch_related('items') \
        .filter(admin__admin_id=admin_id)
    
    # Apply filters
    if customer_filter:
        orders = orders.filter(
            Q(customer__first_name__icontains=customer_filter) |
            Q(customer__last_name__icontains=customer_filter) |
            Q(customer__company_name__icontains=customer_filter)
        )
    
    if date_from and date_to:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(order_date__range=[date_from, date_to])
        except ValueError:
            pass
    
    if payment_status:
        if payment_status == 'paid':
            orders = orders.filter(payment_status=1)
        elif payment_status == 'unpaid':
            orders = orders.filter(payment_status=0)
        elif payment_status == 'partial':
            orders = orders.annotate(
                paid_amount=Coalesce(
                    Sum('payments__amount'),
                    0
                )
            ).filter(paid_amount__gt=0, paid_amount__lt=F('overall_amount'))
    
    if category_filter:
        orders = orders.filter(category=category_filter)
    
    # Final ordering
    orders = orders.order_by('-order_date')
    
    # Get payments for filtered orders
    payments = Payments.objects.select_related("order", "order__customer") \
        .filter(order__in=orders).order_by("-date")
    
    # Calculate statistics
    total_orders = orders.count()
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_order_amount = orders.aggregate(total=Sum('overall_amount'))['total'] or 0
    pending_amount = total_order_amount - total_payments
    
    paid_orders = orders.filter(payment_status=1).count()
    unpaid_orders = orders.filter(payment_status=0).count()
    
    # Category statistics
    category_stats = orders.values('category').annotate(
        count=Count('order_id'),
        total_amount=Sum('overall_amount'),
        paid_amount=Sum(
            Case(When(payment_status=1, then='overall_amount'), default=0, output_field=models.DecimalField())
        )
    ).order_by('-count')
    
    # Top products
    top_products = OrderItems.objects.filter(order__in=orders).values('product_name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('total_amount')
    ).order_by('-total_amount')[:10]
    
    # Monthly trends
    monthly_trends = orders.annotate(
        month=ExtractMonth('order_date'),
        year=ExtractYear('order_date')
    ).values('month', 'year').annotate(
        order_count=Count('order_id'),
        total_amount=Sum('overall_amount')
    ).order_by('year', 'month')
    
    # Payment methods
    payment_methods = payments.values('payment_method').annotate(
        count=Count('payment_id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    
    # Get unique customers and categories for filter dropdowns
    customers = CustomerTable.objects.filter(
        orders__admin__admin_id=admin_id
    ).distinct().order_by('first_name')
    
    categories = orders.exclude(category__isnull=True).exclude(category__exact='') \
        .values_list('category', flat=True).distinct().order_by('category')
    
    context = {
        "orders": orders,
        "payments": payments,
        "statistics": {
            "total_orders": total_orders,
            "total_payments": total_payments,
            "total_order_amount": total_order_amount,
            "pending_amount": pending_amount,
            "paid_orders": paid_orders,
            "unpaid_orders": unpaid_orders,
        },
        "category_stats": category_stats,
        "top_products": top_products,
        "monthly_trends": monthly_trends,
        "payment_methods": payment_methods,
        "customers": customers,
        "categories": categories,
        "filters": {
            "customer": customer_filter,
            "date_from": date_from,
            "date_to": date_to,
            "payment_status": payment_status,
            "category": category_filter,
        }
    }
    
    return render(request, "unified_report_admin.html", context)

@role_required(["superadmin"])
def unified_report_superadmin(request):
    orders = Orders.objects.select_related('customer', 'admin').prefetch_related('items') \
        .all().order_by('-order_date')

    payments = Payments.objects.select_related("order", "order__customer", "order__admin") \
        .all().order_by("-date")

    total_orders = orders.count()
    total_payments = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    total_order_amount = orders.aggregate(total=models.Sum('overall_amount'))['total'] or 0
    pending_amount = total_order_amount - total_payments

    paid_orders = orders.filter(payment_status=1).count()
    unpaid_orders = orders.filter(payment_status=0).count()

    category_stats = orders.values('category').annotate(
        count=models.Count('order_id'),
        total_amount=models.Sum('overall_amount'),
        paid_amount=models.Sum(
            Case(When(payment_status=1, then='overall_amount'), default=0, output_field=models.DecimalField())
        )
    ).order_by('-count')

    top_products = OrderItems.objects.filter(order__in=orders).values('product_name').annotate(
        total_quantity=models.Sum('quantity'),
        total_amount=models.Sum('total_amount')
    ).order_by('-total_amount')[:10]

    monthly_trends = orders.annotate(
        month=ExtractMonth('order_date'),
        year=ExtractYear('order_date')
    ).values('month', 'year').annotate(
        order_count=models.Count('order_id'),
        total_amount=models.Sum('overall_amount')
    ).order_by('year', 'month')

    payment_methods = payments.values('payment_method').annotate(
        count=models.Count('payment_id'),
        total_amount=models.Sum('amount')
    ).order_by('-total_amount')

    context = {
        "orders": orders,
        "payments": payments,
        "statistics": {
            "total_orders": total_orders,
            "total_payments": total_payments,
            "total_order_amount": total_order_amount,
            "pending_amount": pending_amount,
            "paid_orders": paid_orders,
            "unpaid_orders": unpaid_orders,
        },
        "category_stats": category_stats,
        "top_products": top_products,
        "monthly_trends": monthly_trends,
        "payment_methods": payment_methods,
    }

    return render(request, "unified_report_superadmin.html", context)

@role_required(["superadmin", "admin"])
def download_report_excel(request):
    try:
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Get data based on role
        admin_id = request.session.get("user_id")
        role = request.session.get("role")
        
        # Add formatting styles
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 11
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'font_size': 10
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'top',
            'num_format': '#,##0.00',
            'font_size': 10
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'top',
            'num_format': 'dd-mm-yyyy',
            'font_size': 10
        })

        # Create Orders sheet
        orders_sheet = workbook.add_worksheet('Orders Detail')
        orders_sheet.freeze_panes(1, 0)

        # Set column widths for orders sheet
        orders_sheet.set_column('A:A', 12)  # Order ID
        orders_sheet.set_column('B:B', 30)  # Customer Details
        orders_sheet.set_column('C:C', 15)  # Order Date
        orders_sheet.set_column('D:D', 15)  # Delivery Date
        orders_sheet.set_column('E:E', 25)  # Product Details
        orders_sheet.set_column('F:F', 20)  # Batch Number
        orders_sheet.set_column('G:G', 15)  # Expiry Date
        orders_sheet.set_column('H:H', 15)  # Quantity
        orders_sheet.set_column('I:I', 10)  # Unit
        orders_sheet.set_column('J:J', 15)  # Price/Unit
        orders_sheet.set_column('K:K', 15)  # Total Amount
        orders_sheet.set_column('L:L', 20)  # GST
        orders_sheet.set_column('M:M', 20)  # Payment Status
        orders_sheet.set_column('N:N', 20)  # Paid Amount
        orders_sheet.set_column('O:O', 20)  # Balance
        orders_sheet.set_column('P:P', 15)  # Vehicle No
        orders_sheet.set_column('Q:Q', 20)  # Driver Details
        orders_sheet.set_column('R:R', 15)  # Delivery Status

        # Write headers for orders sheet
        headers = [
            'Order ID', 'Customer Details', 'Order Date', 'Delivery Date',
            'Product Details', 'Batch Number', 'Expiry Date', 'Quantity',
            'Unit', 'Price/Unit', 'Total Amount', 'GST', 'Payment Status',
            'Paid Amount', 'Balance Due', 'Vehicle No', 'Driver Details',
            'Delivery Status'
        ]
        
        for col, header in enumerate(headers):
            orders_sheet.write(0, col, header, header_format)

        # Get orders data
        if role == "superadmin":
            orders = Orders.objects.select_related('customer', 'admin').prefetch_related(
                'items', 'payments_set'
            ).all().order_by('-order_date')
        else:
            orders = Orders.objects.select_related('customer', 'admin').prefetch_related(
                'items', 'payments_set'
            ).filter(admin__admin_id=admin_id).order_by('-order_date')

        # Write orders data
        row = 1
        for order in orders:
            items = order.items.all()
            payments = order.payments_set.all()
            total_paid = sum(payment.amount for payment in payments)
            balance = order.overall_amount - total_paid

            payment_status = "Fully Paid" if total_paid >= order.overall_amount else \
                           f"Partially Paid ({(total_paid/order.overall_amount)*100:.1f}%)" if total_paid > 0 else "Unpaid"

            delivery_status = "Delivered" if order.delivery_status == 1 else "Pending"

            customer_details = f"{order.customer.first_name} {order.customer.last_name}\n" \
                             f"Company: {order.customer.company_name}\n" \
                             f"Phone: {order.customer.phone_number}\n" \
                             f"Email: {order.customer.email}"

            driver_details = f"Name: {order.driver_name}\nPhone: {order.driver_ph_no}"

            for item in items:
                col = 0
                # Order details
                orders_sheet.write(row, col, str(order.order_id), cell_format); col += 1
                orders_sheet.write(row, col, customer_details, cell_format); col += 1
                orders_sheet.write_datetime(row, col, order.order_date, date_format); col += 1
                if order.delivery_date:
                    orders_sheet.write_datetime(row, col, order.delivery_date, date_format); col += 1
                else:
                    orders_sheet.write(row, col, "Not Set", cell_format); col += 1
                
                # Product details
                orders_sheet.write(row, col, f"{item.product_name}\n{order.category or 'N/A'}", cell_format); col += 1
                orders_sheet.write(row, col, item.batch_number, cell_format); col += 1
                orders_sheet.write_datetime(row, col, item.expiry_date, date_format); col += 1
                orders_sheet.write_number(row, col, item.quantity, number_format); col += 1
                orders_sheet.write(row, col, item.unit, cell_format); col += 1
                orders_sheet.write_number(row, col, item.price_per_unit, number_format); col += 1
                orders_sheet.write_number(row, col, item.total_amount, number_format); col += 1
                orders_sheet.write(row, col, order.GST or 'N/A', cell_format); col += 1
                orders_sheet.write(row, col, payment_status, cell_format); col += 1
                orders_sheet.write_number(row, col, total_paid, number_format); col += 1
                orders_sheet.write_number(row, col, balance, number_format); col += 1
                orders_sheet.write(row, col, order.lorry_number, cell_format); col += 1
                orders_sheet.write(row, col, driver_details, cell_format); col += 1
                orders_sheet.write(row, col, delivery_status, cell_format)
                
                row += 1

        # Create Payments sheet
        payments_sheet = workbook.add_worksheet('Payments Detail')
        payments_sheet.freeze_panes(1, 0)

        # Set column widths for payments
        payments_sheet.set_column('A:A', 15)  # Payment ID
        payments_sheet.set_column('B:B', 15)  # Order ID
        payments_sheet.set_column('C:C', 30)  # Customer
        payments_sheet.set_column('D:D', 15)  # Amount
        payments_sheet.set_column('E:E', 15)  # Date
        payments_sheet.set_column('F:F', 20)  # Method
        payments_sheet.set_column('G:G', 25)  # Reference
        payments_sheet.set_column('H:H', 30)  # Proof Link

        # Write payment headers
        payment_headers = [
            'Payment ID', 'Order ID', 'Customer', 'Amount',
            'Date', 'Method', 'Reference', 'Proof Link'
        ]
        
        for col, header in enumerate(payment_headers):
            payments_sheet.write(0, col, header, header_format)

        # Get and write payments data
        if role == "superadmin":
            payments = Payments.objects.select_related('order__customer').all().order_by('-date')
        else:
            payments = Payments.objects.select_related('order__customer').filter(
                order__admin__admin_id=admin_id
            ).order_by('-date')

        for row, payment in enumerate(payments, 1):
            if payment.order and payment.order.customer:
                customer_name = f"{payment.order.customer.first_name} {payment.order.customer.last_name}"
            else:
                customer_name = "N/A"

            col = 0
            payments_sheet.write(row, col, str(payment.payment_id), cell_format); col += 1
            payments_sheet.write(row, col, str(payment.order.order_id) if payment.order else 'N/A', cell_format); col += 1
            payments_sheet.write(row, col, customer_name, cell_format); col += 1
            payments_sheet.write_number(row, col, payment.amount, number_format); col += 1
            payments_sheet.write_datetime(row, col, payment.date, date_format); col += 1
            payments_sheet.write(row, col, payment.payment_method, cell_format); col += 1
            payments_sheet.write(row, col, payment.reference, cell_format); col += 1
            payments_sheet.write(row, col, payment.proof_link, cell_format)

        # Create Summary sheet
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:B', 15)

        # Summary formats
        summary_header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'left'
        })
        summary_value_format = workbook.add_format({
            'font_size': 11,
            'align': 'right',
            'num_format': '#,##0.00'
        })

        # Calculate and write summary
        total_orders = orders.count()
        total_order_amount = sum(order.overall_amount for order in orders)
        total_paid = sum(payment.amount for payment in payments)
        delivered_orders = orders.filter(delivery_status=1).count()
        pending_orders = total_orders - delivered_orders

        summary_data = [
            ('Total Orders:', total_orders),
            ('Total Order Value:', total_order_amount),
            ('Total Paid Amount:', total_paid),
            ('Balance Due:', total_order_amount - total_paid),
            ('Delivered Orders:', delivered_orders),
            ('Pending Deliveries:', pending_orders)
        ]

        for row, (label, value) in enumerate(summary_data):
            summary_sheet.write(row, 0, label, summary_header_format)
            summary_sheet.write(row, 1, value, summary_value_format)

        # Add timestamp
        summary_sheet.write(
            len(summary_data) + 1, 
            0, 
            f"Report generated on: {timezone.now().strftime('%d %B %Y at %I:%M %p')}",
            workbook.add_format({'font_size': 10, 'italic': True})
        )

        # Close and return
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="detailed_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating Excel report: {str(e)}")
        return redirect('unified_report')
from .models import Orders  # Assuming Orders and OrderItems are in the same app
from paddy_app.decorators import role_required  # Adjust based on your project structure
import inflect
@role_required(["admin"])
def download_invoice_pdf(request):
    admin_id = request.session.get("user_id")
    role = request.session.get("role")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="business_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'

    # Document setup with professional margins
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica',
        leading=9
    )
    
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold',
        spaceAfter=5
    )

    # Header with title and admin info
    elements.append(Paragraph("Business Order Report", title_style))
    
    # Add admin information if available
    if role == "admin":
        admin = AdminTable.objects.get(admin_id=admin_id)
        admin_info = f"Generated by: {admin.first_name} {admin.last_name} | {admin.email} | {timezone.now().strftime('%d %B %Y at %I:%M %p')}"
        elements.append(Paragraph(admin_info, subtitle_style))
    
    # Add a horizontal line
    elements.append(HRFlowable(
        width="100%",
        thickness=1,
        lineCap='round',
        color=colors.HexColor('#bdc3c7'),
        spaceAfter=15
    ))

    # Table data setup
    table_data = [[
        Paragraph("Order ID", header_style),
        Paragraph("Customer", header_style),
        Paragraph("Order Date", header_style),
        Paragraph("Delivery", header_style),
        Paragraph("Product", header_style),
        Paragraph("Batch/Expiry", header_style),
        Paragraph("Qty/Unit", header_style),
        Paragraph("Price", header_style),
        Paragraph("Total", header_style),
        Paragraph("Payment", header_style),
        Paragraph("Status", header_style)
    ]]

    # Query data based on role
    if role == "superadmin":
        orders = Orders.objects.select_related("customer", "admin").prefetch_related(
            "items", "payments_set"
        ).all().order_by('-order_date')
    else:
        orders = Orders.objects.select_related("customer", "admin").prefetch_related(
            "items", "payments_set"
        ).filter(admin__admin_id=admin_id).order_by('-order_date')

    for order in orders:
        customer = order.customer
        order_items = order.items.all()
        payments = order.payments_set.all()

        total_paid = sum(payment.amount for payment in payments)
        payment_status = "Unpaid" if total_paid == 0 else \
                        "Fully Paid" if total_paid >= order.overall_amount else \
                        f"Paid: {total_paid/order.overall_amount:.0%}"

        delivery_status = "Delivered" if order.delivery_status == 1 else "Pending"

        customer_details = Paragraph(
            f"<b>{customer.first_name} {customer.last_name}</b><br/>"
            f"{customer.company_name or ''}<br/>"
            f"GST: {customer.GST or 'N/A'}<br/>"
            f"Ph: {customer.phone_number}",
            cell_style
        )

        for idx, item in enumerate(order_items):
            payment_details = []
            if idx == 0:
                for payment in payments:
                    payment_details.append(
                        f"<b>₹{payment.amount:,.2f}</b> "
                        f"({payment.date.strftime('%d-%m-%Y')})<br/>"
                        f"{payment.payment_method} "
                        f"Ref: {payment.reference}"
                    )
            payment_info = "\n".join(payment_details) if payment_details else f"<b>Due:</b> ₹{order.overall_amount - total_paid:,.2f}"

            product_details = Paragraph(
                f"<b>{item.product_name}</b><br/>"
                f"{order.category or 'N/A'}",
                cell_style
            )
            
            batch_expiry = Paragraph(
                f"<b>Batch:</b> {item.batch_number}<br/>"
                f"<b>Exp:</b> {item.expiry_date.strftime('%d-%m-%Y')}",
                cell_style
            )
            
            qty_unit = Paragraph(
                f"{item.quantity:,.2f} {item.unit}",
                cell_style
            )

            row = [
                Paragraph(str(order.order_id) if idx == 0 else "", cell_style),
                customer_details if idx == 0 else Paragraph("", cell_style),
                Paragraph(order.order_date.strftime("%d-%m-%Y") if idx == 0 else "", cell_style),
                Paragraph(order.delivery_date.strftime("%d-%m-%Y") if order.delivery_date and idx == 0 else "Not Set", cell_style),
                product_details,
                batch_expiry,
                qty_unit,
                Paragraph(f"₹{item.price_per_unit:,.2f}", cell_style),
                Paragraph(f"<b>₹{item.total_amount:,.2f}</b>", cell_style),
                Paragraph(payment_info if idx == 0 else "", cell_style),
                Paragraph(
                    f"<b>{delivery_status}</b><br/>"
                    f"{order.lorry_number or ''}<br/>"
                    f"{order.driver_name or ''}<br/>"
                    f"Ph: {order.driver_ph_no or ''}" if idx == 0 else "",
                    cell_style
                )
            ]
            table_data.append(row)

        # Add subtle separator between orders
        if orders.last() != order:
            table_data.append([Paragraph("—"*5, cell_style) for _ in range(11)])

    # Column widths adjusted for better readability
    col_widths = [40, 80, 50, 50, 80, 70, 50, 50, 50, 80, 80]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ALIGN', (7, 1), (8, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Professional summary section
    total_orders = orders.count()
    total_order_amount = sum(order.overall_amount for order in orders)
    total_paid = sum(payment.amount for order in orders for payment in order.payments_set.all())
    delivered_orders = orders.filter(delivery_status=1).count()
    pending_orders = total_orders - delivered_orders

    summary_elements = []
    
    # Summary title
    summary_elements.append(Paragraph("Business Performance Summary", summary_style))
    summary_elements.append(HRFlowable(
        width="100%",
        thickness=0.5,
        lineCap='round',
        color=colors.HexColor('#bdc3c7'),
        spaceAfter=10
    ))
    
    # Key metrics in a table
    summary_table_data = [
        [
            Paragraph("<b>Metric</b>", summary_style),
            Paragraph("<b>Value</b>", summary_style),
            Paragraph("<b>Metric</b>", summary_style),
            Paragraph("<b>Value</b>", summary_style)
        ],
        [
            Paragraph("Total Orders", cell_style),
            Paragraph(f"{total_orders}", cell_style),
            Paragraph("Delivered Orders", cell_style),
            Paragraph(f"{delivered_orders} ({delivered_orders/total_orders:.0%})", cell_style)
        ],
        [
            Paragraph("Total Order Value", cell_style),
            Paragraph(f"₹{total_order_amount:,.2f}", cell_style),
            Paragraph("Pending Deliveries", cell_style),
            Paragraph(f"{pending_orders} ({pending_orders/total_orders:.0%})", cell_style)
        ],
        [
            Paragraph("Total Payments Received", cell_style),
            Paragraph(f"₹{total_paid:,.2f}", cell_style),
            Paragraph("Outstanding Balance", cell_style),
            Paragraph(f"₹{(total_order_amount - total_paid):,.2f}", cell_style)
        ],
        [
            Paragraph("Payment Completion", cell_style),
            Paragraph(f"{(total_paid/total_order_amount):.0%}", cell_style),
            Paragraph("Average Order Value", cell_style),
            Paragraph(f"₹{total_order_amount/total_orders:,.2f}", cell_style)
        ]
    ]
    
    summary_table = Table(summary_table_data, colWidths=[100, 80, 100, 80])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f1f1')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]))
    
    summary_elements.append(summary_table)
    summary_elements.append(Spacer(1, 15))
    
    # Footer note
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica-Oblique'
    )
    summary_elements.append(Paragraph("This report contains confidential business information. Unauthorized use is prohibited.", footer_style))
    
    elements.extend(summary_elements)

    doc.build(elements)
    return response
@role_required(["superadmin"])
def download_invoice_pdf1(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="superadmin_report_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'

    # Document setup with professional margins
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica',
        leading=9
    )
    
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold',
        spaceAfter=5
    )

    # Header with logo and title
    elements.append(Paragraph("Superadmin Business Report", title_style))
    elements.append(Paragraph(f"Orders & Payments Analysis | Generated on {timezone.now().strftime('%d %B %Y at %I:%M %p')}", subtitle_style))
    
    # Add a horizontal line
    elements.append(HRFlowable(
        width="100%",
        thickness=1,
        lineCap='round',
        color=colors.HexColor('#bdc3c7'),
        spaceAfter=15
    ))

    # Table data setup
    table_data = [[
        Paragraph("Order ID", header_style),
        Paragraph("Admin", header_style),
        Paragraph("Customer", header_style),
        Paragraph("Order Date", header_style),
        Paragraph("Delivery", header_style),
        Paragraph("Product", header_style),
        Paragraph("Batch/Expiry", header_style),
        Paragraph("Qty/Unit", header_style),
        Paragraph("Price", header_style),
        Paragraph("Total", header_style),
        Paragraph("Payment", header_style),
        Paragraph("Status", header_style)
    ]]

    # Query optimization
    orders = Orders.objects.select_related("customer", "admin")\
                          .prefetch_related("items", "payments_set")\
                          .all().order_by('-order_date')

    for order in orders:
        customer = order.customer
        admin = order.admin
        order_items = order.items.all()
        payments = order.payments_set.all()

        total_paid = sum(payment.amount for payment in payments)
        payment_status = "Unpaid" if total_paid == 0 else \
                        "Fully Paid" if total_paid >= order.overall_amount else \
                        f"Paid: {total_paid/order.overall_amount:.0%}"

        delivery_status = "Delivered" if order.delivery_status == 1 else "Pending"

        customer_details = Paragraph(
            f"<b>{customer.first_name} {customer.last_name}</b><br/>"
            f"{customer.company_name or ''}<br/>"
            f"GST: {customer.GST or 'N/A'}<br/>"
            f"Ph: {customer.phone_number}",
            cell_style
        )

        admin_details = Paragraph(
            f"<b>{admin.first_name} {admin.last_name}</b><br/>"
            f"Email: {admin.email}<br/>"
            f"Ph: {admin.phone_number}",
            cell_style
        )

        for idx, item in enumerate(order_items):
            payment_details = []
            if idx == 0:
                for payment in payments:
                    payment_details.append(
                        f"<b>₹{payment.amount:,.2f}</b> "
                        f"({payment.date.strftime('%d-%m-%Y')})<br/>"
                        f"{payment.payment_method} "
                        f"Ref: {payment.reference}"
                    )
            payment_info = "\n".join(payment_details) if payment_details else f"<b>Due:</b> ₹{order.overall_amount - total_paid:,.2f}"

            product_details = Paragraph(
                f"<b>{item.product_name}</b><br/>"
                f"{order.category or 'N/A'}",
                cell_style
            )
            
            batch_expiry = Paragraph(
                f"<b>Batch:</b> {item.batch_number}<br/>"
                f"<b>Exp:</b> {item.expiry_date.strftime('%d-%m-%Y')}",
                cell_style
            )
            
            qty_unit = Paragraph(
                f"{item.quantity:,.2f} {item.unit}",
                cell_style
            )

            row = [
                Paragraph(str(order.order_id) if idx == 0 else "", cell_style),
                admin_details if idx == 0 else Paragraph("", cell_style),
                customer_details if idx == 0 else Paragraph("", cell_style),
                Paragraph(order.order_date.strftime("%d-%m-%Y") if idx == 0 else "", cell_style),
                Paragraph(order.delivery_date.strftime("%d-%m-%Y") if order.delivery_date and idx == 0 else "Not Set", cell_style),
                product_details,
                batch_expiry,
                qty_unit,
                Paragraph(f"₹{item.price_per_unit:,.2f}", cell_style),
                Paragraph(f"<b>₹{item.total_amount:,.2f}</b>", cell_style),
                Paragraph(payment_info if idx == 0 else "", cell_style),
                Paragraph(
                    f"<b>{delivery_status}</b><br/>"
                    f"{order.lorry_number or ''}<br/>"
                    f"{order.driver_name or ''}<br/>"
                    f"Ph: {order.driver_ph_no or ''}" if idx == 0 else "",
                    cell_style
                )
            ]
            table_data.append(row)

        # Add subtle separator between orders
        if orders.last() != order:
            table_data.append([Paragraph("—"*5, cell_style) for _ in range(12)])

    # Column widths adjusted for better readability
    col_widths = [35, 75, 75, 45, 45, 75, 60, 40, 45, 45, 75, 70]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ALIGN', (7, 1), (9, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Professional summary section
    total_orders = orders.count()
    total_order_amount = sum(order.overall_amount for order in orders)
    total_paid = sum(payment.amount for order in orders for payment in order.payments_set.all())
    delivered_orders = orders.filter(delivery_status=1).count()
    pending_orders = total_orders - delivered_orders

    summary_elements = []
    
    # Summary title
    summary_elements.append(Paragraph("Business Performance Summary", summary_style))
    summary_elements.append(HRFlowable(
        width="100%",
        thickness=0.5,
        lineCap='round',
        color=colors.HexColor('#bdc3c7'),
        spaceAfter=10
    ))
    
    # Key metrics in a table
    summary_table_data = [
        [
            Paragraph("<b>Metric</b>", summary_style),
            Paragraph("<b>Value</b>", summary_style),
            Paragraph("<b>Metric</b>", summary_style),
            Paragraph("<b>Value</b>", summary_style)
        ],
        [
            Paragraph("Total Orders", cell_style),
            Paragraph(f"{total_orders}", cell_style),
            Paragraph("Delivered Orders", cell_style),
            Paragraph(f"{delivered_orders} ({delivered_orders/total_orders:.0%})", cell_style)
        ],
        [
            Paragraph("Total Order Value", cell_style),
            Paragraph(f"₹{total_order_amount:,.2f}", cell_style),
            Paragraph("Pending Deliveries", cell_style),
            Paragraph(f"{pending_orders} ({pending_orders/total_orders:.0%})", cell_style)
        ],
        [
            Paragraph("Total Payments Received", cell_style),
            Paragraph(f"₹{total_paid:,.2f}", cell_style),
            Paragraph("Outstanding Balance", cell_style),
            Paragraph(f"₹{(total_order_amount - total_paid):,.2f}", cell_style)
        ],
        [
            Paragraph("Payment Completion", cell_style),
            Paragraph(f"{(total_paid/total_order_amount):.0%}", cell_style),
            Paragraph("Average Order Value", cell_style),
            Paragraph(f"₹{total_order_amount/total_orders:,.2f}", cell_style)
        ]
    ]
    
    summary_table = Table(summary_table_data, colWidths=[100, 80, 100, 80])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f1f1')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]))
    
    summary_elements.append(summary_table)
    summary_elements.append(Spacer(1, 15))
    
    # Footer note
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica-Oblique'
    )
    summary_elements.append(Paragraph("This report contains confidential business information. Unauthorized use is prohibited.", footer_style))
    
    elements.extend(summary_elements)

    doc.build(elements)
    return response



@role_required(["superadmin", "admin"])
def download_invoice_excel1(request):
    try:
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        admin_id = request.session.get("user_id")
        role = request.session.get("role")

        # Formatting styles
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 11
        })
        cell_format = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True, 'font_size': 10
        })
        number_format = workbook.add_format({
            'border': 1, 'align': 'right', 'valign': 'top', 'num_format': '#,##0.00', 'font_size': 10
        })
        date_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'top', 'num_format': 'dd-mm-yyyy', 'font_size': 10
        })

        # Orders Sheet
        orders_sheet = workbook.add_worksheet('Orders Detail')
        orders_sheet.freeze_panes(1, 0)

        # Column widths
        orders_sheet.set_column('A:A', 12)
        orders_sheet.set_column('B:B', 30)
        orders_sheet.set_column('C:C', 30)  # Admin Details
        orders_sheet.set_column('D:D', 15)
        orders_sheet.set_column('E:E', 15)
        orders_sheet.set_column('F:F', 25)
        orders_sheet.set_column('G:G', 20)
        orders_sheet.set_column('H:H', 15)
        orders_sheet.set_column('I:I', 10)
        orders_sheet.set_column('J:J', 15)
        orders_sheet.set_column('K:K', 15)
        orders_sheet.set_column('L:L', 20)
        orders_sheet.set_column('M:M', 20)
        orders_sheet.set_column('N:N', 20)
        orders_sheet.set_column('O:O', 20)
        orders_sheet.set_column('P:P', 15)
        orders_sheet.set_column('Q:Q', 20)
        orders_sheet.set_column('R:R', 15)

        headers = [
            'Order ID', 'Customer Details', 'Admin Details', 'Order Date', 'Delivery Date',
            'Product Details', 'Batch Number', 'Expiry Date', 'Quantity', 'Unit', 'Price/Unit',
            'Total Amount', 'GST', 'Payment Status', 'Paid Amount', 'Balance Due',
            'Vehicle No', 'Driver Details', 'Delivery Status'
        ]
        for col, header in enumerate(headers):
            orders_sheet.write(0, col, header, header_format)

        # Fetch Orders
        if role == "superadmin":
            orders = Orders.objects.select_related('customer', 'admin').prefetch_related('items', 'payments_set').all().order_by('-order_date')
        else:
            orders = Orders.objects.select_related('customer', 'admin').prefetch_related('items', 'payments_set').filter(admin__admin_id=admin_id).order_by('-order_date')

        # Write Order Data
        row = 1
        for order in orders:
            items = order.items.all()
            payments = order.payments_set.all()
            total_paid = sum(p.amount for p in payments)
            balance = order.overall_amount - total_paid

            payment_status = "Fully Paid" if total_paid >= order.overall_amount else \
                             f"Partially Paid ({(total_paid/order.overall_amount)*100:.1f}%)" if total_paid > 0 else "Unpaid"
            delivery_status = "Delivered" if order.delivery_status == 1 else "Pending"

            customer_details = f"{order.customer.first_name} {order.customer.last_name}\nCompany: {order.customer.company_name}\nPhone: {order.customer.phone_number}\nEmail: {order.customer.email}"
            driver_details = f"Name: {order.driver_name}\nPhone: {order.driver_ph_no}"
            admin_details = f"{order.admin.first_name} {order.admin.last_name}\nPhone: {order.admin.phone_number}\nEmail: {order.admin.email}" if role == "superadmin" else "N/A"

            for item in items:
                col = 0
                orders_sheet.write(row, col, str(order.order_id), cell_format); col += 1
                orders_sheet.write(row, col, customer_details, cell_format); col += 1
                orders_sheet.write(row, col, admin_details, cell_format); col += 1
                orders_sheet.write_datetime(row, col, order.order_date, date_format); col += 1
                if order.delivery_date:
                    orders_sheet.write_datetime(row, col, order.delivery_date, date_format); col += 1
                else:
                    orders_sheet.write(row, col, "Not Set", cell_format); col += 1
                orders_sheet.write(row, col, f"{item.product_name}\n{order.category or 'N/A'}", cell_format); col += 1
                orders_sheet.write(row, col, item.batch_number, cell_format); col += 1
                orders_sheet.write_datetime(row, col, item.expiry_date, date_format); col += 1
                orders_sheet.write_number(row, col, item.quantity, number_format); col += 1
                orders_sheet.write(row, col, item.unit, cell_format); col += 1
                orders_sheet.write_number(row, col, item.price_per_unit, number_format); col += 1
                orders_sheet.write_number(row, col, item.total_amount, number_format); col += 1
                orders_sheet.write(row, col, order.GST or 'N/A', cell_format); col += 1
                orders_sheet.write(row, col, payment_status, cell_format); col += 1
                orders_sheet.write_number(row, col, total_paid, number_format); col += 1
                orders_sheet.write_number(row, col, balance, number_format); col += 1
                orders_sheet.write(row, col, order.lorry_number, cell_format); col += 1
                orders_sheet.write(row, col, driver_details, cell_format); col += 1
                orders_sheet.write(row, col, delivery_status, cell_format)
                row += 1

        # Payments Sheet
        payments_sheet = workbook.add_worksheet('Payments Detail')
        payments_sheet.freeze_panes(1, 0)
        payments_sheet.set_column('A:H', 20)

        payment_headers = [
            'Payment ID', 'Order ID', 'Customer', 'Amount', 'Date',
            'Method', 'Reference', 'Proof Link'
        ]
        for col, header in enumerate(payment_headers):
            payments_sheet.write(0, col, header, header_format)

        if role == "superadmin":
            payments = Payments.objects.select_related('order__customer').all().order_by('-date')
        else:
            payments = Payments.objects.select_related('order__customer').filter(order__admin__admin_id=admin_id).order_by('-date')

        for row, payment in enumerate(payments, 1):
            customer_name = f"{payment.order.customer.first_name} {payment.order.customer.last_name}" if payment.order and payment.order.customer else "N/A"
            col = 0
            payments_sheet.write(row, col, str(payment.payment_id), cell_format); col += 1
            payments_sheet.write(row, col, str(payment.order.order_id) if payment.order else 'N/A', cell_format); col += 1
            payments_sheet.write(row, col, customer_name, cell_format); col += 1
            payments_sheet.write_number(row, col, payment.amount, number_format); col += 1
            payments_sheet.write_datetime(row, col, payment.date, date_format); col += 1
            payments_sheet.write(row, col, payment.payment_method, cell_format); col += 1
            payments_sheet.write(row, col, payment.reference, cell_format); col += 1
            payments_sheet.write(row, col, payment.proof_link, cell_format)

        # Summary Sheet
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:B', 30)

        summary_header_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'left'})
        summary_value_format = workbook.add_format({'font_size': 11, 'align': 'right', 'num_format': '#,##0.00'})

        total_orders = orders.count()
        total_order_amount = sum(order.overall_amount for order in orders)
        total_paid = sum(payment.amount for payment in payments)
        delivered_orders = orders.filter(delivery_status=1).count()
        pending_orders = total_orders - delivered_orders

        summary_data = [
            ('Total Orders:', total_orders),
            ('Total Order Value:', total_order_amount),
            ('Total Paid Amount:', total_paid),
            ('Balance Due:', total_order_amount - total_paid),
            ('Delivered Orders:', delivered_orders),
            ('Pending Deliveries:', pending_orders)
        ]
        for row, (label, value) in enumerate(summary_data):
            summary_sheet.write(row, 0, label, summary_header_format)
            summary_sheet.write(row, 1, value, summary_value_format)

        # Per Admin Orders (for superadmin only)
        if role == "superadmin":
            from collections import Counter
            admin_counts = Counter(order.admin for order in orders)
            offset = len(summary_data) + 2
            summary_sheet.write(offset - 1, 0, "Orders Per Admin:", summary_header_format)
            for i, (admin, count) in enumerate(admin_counts.items()):
                summary_sheet.write(offset + i, 0, f"{admin.first_name} {admin.last_name}", summary_header_format)
                summary_sheet.write(offset + i, 1, count, summary_value_format)

        # Timestamp
        summary_sheet.write(
            len(summary_data) + 10,
            0,
            f"Report generated on: {timezone.now().strftime('%d %B %Y at %I:%M %p')}",
            workbook.add_format({'font_size': 10, 'italic': True})
        )

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="detailed_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        return response

    except Exception as e:
        messages.error(request, f"Error generating Excel report: {str(e)}")
        return redirect('unified_report')