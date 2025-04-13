from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from .models import *
from django.db import IntegrityError
from datetime import date
from django.core.paginator import Paginator
from django.utils import timezone
from .decorators import role_required
import json
from django.shortcuts import render, get_object_or_404, redirect


def login_view(request):
    # Redirect already logged-in users based on their role
    if request.session.get("user_id") and request.session.get("role"):
        role = request.session["role"]
        if role == "superadmin":
            return redirect("superadmin_dashboard")
        elif role == "admin":
            return redirect("admin_dashboard")
        elif role == "customer":
            return redirect("customer_dashboard")

    if request.method == "POST":
        phone_number = request.POST.get("username")  # Phone number as username
        password = request.POST.get("password")
        role = request.POST.get("role")  # Role from dropdown

        if not phone_number or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("login")

        # Super Admin Login
        if role == "superadmin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)

                if user.admin_id > 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")

                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "superadmin"
                    messages.success(request, "Login successful!")
                    return redirect("superadmin_dashboard")
                else:
                    messages.error(request, "Invalid password.")
            except AdminTable.DoesNotExist:
                messages.error(request, "Super Admin not found.")

        # Admin Login
        elif role == "admin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)

                if user.admin_id == 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")

                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "admin"
                    messages.success(request, "Login successful!")
                    return redirect("admin_dashboard")
                else:
                    messages.error(request, "Invalid password.")
            except AdminTable.DoesNotExist:
                messages.error(request, "Admin not found.")

        # Customer Login
        elif role == "customer":
            try:
                user = CustomerTable.objects.get(phone_number=phone_number)
                if check_password(password, user.password):
                    request.session["user_id"] = user.customer_id
                    request.session["role"] = "customer"
                    messages.success(request, "Login successful!")
                    return redirect("customer_dashboard")
                else:
                    messages.error(request, "Invalid password.")
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

        # Check if customer limit is reached
        current_customer_count = CustomerTable.objects.filter(admin=admin).count()
        if current_customer_count >= admin.user_count:
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
            CustomerTable.objects.create(
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

            messages.success(request, "Customer created successfully!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "onboard.html" if is_superadmin else "customer_onboard.html")

@role_required(["superadmin", "admin"])
def place_order(request):
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login")

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        product_category_id = request.POST.get("product_category_id")
        quantity = request.POST.get("quantity")
        price_per_unit = request.POST.get("price_per_unit")
        lorry_number = request.POST.get("lorry_number")
        driver_name = request.POST.get("driver_name")
        driver_ph_no = request.POST.get("driver_ph_no")
        delivery_date = request.POST.get("delivery_date")

        try:
            customer = CustomerTable.objects.get(customer_id=customer_id)
            gst = customer.GST

            quantity = float(quantity) if quantity else 0
            price_per_unit = float(price_per_unit) if price_per_unit else 0
            overall_amount = quantity * price_per_unit

            Orders.objects.create(
                customer=customer,
                admin=AdminTable.objects.get(admin_id=admin_id),
                payment_status=0,
                delivery_status=0,
                product_category_id=product_category_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
                overall_amount=overall_amount,
                GST=gst,
                lorry_number=lorry_number,
                driver_name=driver_name,
                delivery_date=delivery_date,
                driver_ph_no=driver_ph_no,
                order_date=date.today()
            )

            return redirect("place_order" if is_superadmin else "admin_place_order")

        except Exception as e:
            print("Error placing order:", e)

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
            'product_category_id': order.product_category_id
        } for order in orders]
        
        return JsonResponse({'orders': orders_data})
    
    # For regular page load, just render the template (JS will fetch data)
    return render(request, 'customer_order.html')

def payment(request):
    return render(request, 'payment.html')

def customer_delivery_validation(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        delivery_status = request.POST.get('delivery_status')

        try:
            order = Orders.objects.get(order_id=order_id)
            order.delivery_status = delivery_status
            order.save()
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
    admin = AdminTable.objects.get(admin_id=user_id)
    user_count = admin.user_count
    existing_subscription = Subscription.objects.filter(admin_id=user_id, subscription_type=1).first()
    print(existing_subscription)
    if request.method == "POST":
        if request.POST.get("submission_type") == '0': 
            try:
                Subscription.objects.create(
                    admin_id=admin,
                    subscription_type=1, # 1 is for admin user addition
                    additional_users=50, # 50 is the default value for admin user addition
                )
                messages.success(request, "Subscription Request added successfully!")
            except Exception:
                messages.error(request, "Failed to add subscription. Please try again.")
    return render(request, "admin_add_subscription.html", {"user_count": user_count,
                                                        "added_count":user_count+50,
                                                        "existing_subscription": 1 if existing_subscription else 0,
                                                        "payment_amount": existing_subscription.payment_amount if existing_subscription else 0,
                                                        "subscription_status": existing_subscription.subscription_status if existing_subscription else 0,
                                                        })

@role_required(["superadmin"])
def super_admin_subscription(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    subscriptions_queryset = Subscription.objects.filter(subscription_type='1').order_by('-sid')
    
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
    
    return render(request, 'super_admin_subscription.html', context)

@role_required(["superadmin"])
def superadmin_subscription_review(request):
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription_id')
        subscription_status = request.POST.get('subscription_status')
        payment_amount = request.POST.get('payment_amount')
        try:
            subscription = Subscription.objects.get(sid=subscription_id)
            
            # Update subscription
            subscription.subscription_status = subscription_status
            
            if subscription_status == '1':  # If approved
                subscription.payment_amount = payment_amount
                messages.success(request, f"Subscription request #{subscription_id} has been approved.")
            elif subscription_status == '2':  # If rejected
                messages.info(request, f"Subscription request #{subscription_id} has been rejected.")
            
            subscription.save()
            
        except Subscription.DoesNotExist:
            messages.error(request, "Subscription request not found.")
        
        return redirect('superadmin_subscription_review')
    
    # If not POST, redirect to the list view
    return redirect('superadmin_subscription_review')

@role_required(["customer"])
def upgrade_to_admin(request):
    customer_id = request.session.get('user_id')

    customer = CustomerTable.objects.get(customer_id=customer_id)

    if request.method == 'POST':
        if AdminTable.objects.filter(email=customer.email).exists():
            messages.info(request, "You are already an admin.")
            return redirect('customer_dashboard')

        new_admin = AdminTable(
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone_number=customer.phone_number,
            email=customer.email,
            password=customer.password,  # already hashed
            user_count=0,
        )
        new_admin.save()
        messages.success(request, "You have been upgraded to admin!")
        return redirect('customer_dashboard')

    return render(request, 'upgrade_to_admin.html', {'customer': customer})

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')

@role_required(["superadmin"])
def view_admins(request):
    admins = AdminTable.objects.exclude(admin_id=1000000)
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

def demo(request):
    return render(request, 'demo.html')