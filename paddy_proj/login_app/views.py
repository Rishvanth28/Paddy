from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from django.utils.timezone import now
from datetime import timedelta
from paddy_app.models import AdminTable, CustomerTable, Subscription
from paddy_app.helpers import create_notification, validate_gst

def login_view(request):
    if request.session.get("user_id") and request.session.get("role"):
        role = request.session["role"]
        if role == "superadmin":
            return redirect("superadmin_app:superadmin_dashboard")
        elif role == "admin":
            return redirect("admin_app:admin_dashboard")
        elif role == "customer":
            return redirect("customer_app:customer_dashboard")

    if request.method == "POST":
        phone_number = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        if not phone_number or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("login_app:login")

        if role == "superadmin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id > 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login_app:login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "superadmin"
                    return redirect("superadmin_app:superadmin_dashboard")
            except AdminTable.DoesNotExist:
                messages.error(request, "Super Admin not found.")

        elif role == "admin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id == 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login_app:login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "admin"
                    sub = Subscription.objects.filter(admin_id=user, subscription_type="admin").order_by("-end_date").first()
                    if sub and sub.end_date and sub.end_date >= now().date():
                        return redirect("admin_app:admin_dashboard")
                    else:
                        return redirect("admin_app:admin_subscription_payment")
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
                            return redirect("customer_app:customer_dashboard")
                        else:
                            return redirect("customer_app:customer_subscription_payment")
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
                        return redirect("customer_app:customer_dashboard")
            except CustomerTable.DoesNotExist:
                messages.error(request, "Customer not found.")

        else:
            messages.error(request, "Invalid role selected.")

    return render(request, "login.html")   

def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login_app:login")

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
            return redirect("login_app:login")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("login_app:login")

        try:
            AdminTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=make_password(password),
                user_count=50
            )
            messages.success(request, "Admin created successfully!")
            return redirect("login_app:login")
        except IntegrityError:
            messages.error(request, "Failed to create admin. Please try again.")
            messages.warning(request, "This email is already registered.")
            messages.info(request, "Please fill all required fields.")
            
    return render(request, "login.html")


def create_customer_signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        gst = request.POST.get("gst")
        address = request.POST.get("address")
        
        # Default to superadmin ID for self-signup customers
        # In a real application, you might want to assign them to the most appropriate admin
        # or have a more sophisticated assignment logic
        admin_id = 1000000  # SuperAdmin ID
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
            return redirect("login_app:login")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("login_app:login")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("login_app:login")

        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("login_app:login")

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
            return redirect("login_app:login")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "login.html")


def admin_login_submit(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            admin = AdminTable.objects.get(email=email)
            if check_password(password, admin.password):
                request.session['user_id'] = admin.admin_id
                request.session['role'] = 'admin'
                return redirect('admin_app:admin_customer_list')
        except AdminTable.DoesNotExist:
            pass
    return render(request, 'login.html', {'error': 'Invalid credentials'})


def swap_role(request):
    """
    Allows users to switch between admin and customer roles if they have both accounts
    """
    user_id = request.session.get('user_id')
    current_role = request.session.get('role')
    
    if not user_id or not current_role:
        messages.error(request, "Session expired. Please log in again.")
        return redirect("login_app:login")
        
    if current_role == 'admin':
        try:
            admin = AdminTable.objects.get(admin_id=user_id)
            # Try to find a customer with the same email
            try:
                customer = CustomerTable.objects.get(email=admin.email)
                # Switch to customer role
                request.session['user_id'] = customer.customer_id
                request.session['role'] = 'customer'
                messages.success(request, "Switched to customer account.")
                return redirect("customer_app:customer_dashboard")
            except CustomerTable.DoesNotExist:
                messages.error(request, "You don't have a customer account.")
                return redirect("admin_app:admin_dashboard")
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin account not found.")
            return redirect("login_app:login")
            
    elif current_role == 'customer':
        try:
            customer = CustomerTable.objects.get(customer_id=user_id)
            # Try to find an admin with the same email
            try:
                admin = AdminTable.objects.get(email=customer.email)
                # Switch to admin role
                request.session['user_id'] = admin.admin_id
                request.session['role'] = 'admin'
                messages.success(request, "Switched to admin account.")
                return redirect("admin_app:admin_dashboard")
            except AdminTable.DoesNotExist:
                messages.error(request, "You don't have an admin account.")
                return redirect("customer_app:customer_dashboard")
        except CustomerTable.DoesNotExist:
            messages.error(request, "Customer account not found.")
            return redirect("login_app:login")
    
    # Default case (should not happen)
    return redirect("login_app:login")
