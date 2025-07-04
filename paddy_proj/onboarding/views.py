from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.utils.timezone import now
from datetime import timedelta
from paddy_app.models import AdminTable, CustomerTable, Subscription
from paddy_app.decorators import role_required
from paddy_app.helpers import validate_gst, create_notification


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
            return redirect("onboarding:onboard")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("onboarding:onboard")

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
            return redirect("onboarding:onboard")
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
            return redirect("onboarding:onboard" if is_superadmin else "onboarding:customer_onboard_view")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("onboarding:onboard" if is_superadmin else "onboarding:customer_onboard_view")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("onboarding:onboard" if is_superadmin else "onboarding:customer_onboard_view")

        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("onboarding:onboard" if is_superadmin else "onboarding:customer_onboard_view")

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
            return redirect("onboarding:onboard" if is_superadmin else "onboarding:customer_onboard_view")

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
                password=password,
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

        admin_id = 1000000
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


@role_required(["admin"])
def customer_onboard_view(request):
    return render(request, "customer_onboard.html")
