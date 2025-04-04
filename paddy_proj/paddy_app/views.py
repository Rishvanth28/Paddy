from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import *
from django.db import IntegrityError

def login_view(request):
    if request.method == "POST":
        phone_number = request.POST.get("username")  # Phone number as username
        password = request.POST.get("password")
        role = request.POST.get("role")  # Role from dropdown

        if not phone_number or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("login")

        # Super Admin Login (admin_id < 1000)
        if role == "superadmin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                
                if user.admin_id >= 1000:  #  Ensure only super admins can log in
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")

                if check_password(password, user.password):  # If password is hashed
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "superadmin"
                    messages.success(request, "Login successful!")
                    return redirect("superadmin_dashboard")
                else:
                    messages.error(request, "Invalid password.")
            except AdminTable.DoesNotExist:
                messages.error(request, "Super Admin not found.")

        # Admin Login (admin_id >= 1000)
        elif role == "admin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)

                if user.admin_id < 1000:  #  Prevent Super Admins from logging in as Admins
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")

                if check_password(password, user.password):  # If password is hashed
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
                if check_password(password, user.password):  # If password is hashed
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

def superadmin_dashboard(request):
    if request.session.get("role") != "superadmin":
        messages.error(request, "Unauthorized access.")
        return redirect("login")
    return render(request, "superadmin_dashboard.html")

def admin_dashboard(request):
    if request.session.get("role") != "admin":
        messages.error(request, "Unauthorized access.")
        return redirect("login")
    return render(request, "admin_dashboard.html")

def customer_dashboard(request):
    if request.session.get("role") != "customer":
        messages.error(request, "Unauthorized access.")
        return redirect("login")
    return render(request, "customer_dashboard.html")


def validate_gst(gst):
    gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gst_pattern, gst))


def onboard(request):
    return render(request, "onboard.html")

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
            )
            messages.success(request, "Admin created successfully!")
            return redirect("onboard")
        except IntegrityError:
            messages.error(request, "Failed to create admin. Please try again.")

    return render(request, "onboard.html")


def create_customer(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        gst = request.POST.get("gst")

        # Retrieve the currently logged-in admin
        admin_id = request.session.get("user_id")
          # Debugging line
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login")

        # Check for duplicate email or phone number
        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("onboard")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("onboard")

        # Validate GST format if provided
        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("onboard")

        try:
            # Create customer with hashed password
            customer = CustomerTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=make_password(password),  # Hashing the password
                company_name=company_name,
                GST=gst if gst else None,  # Store GST only if provided
                admin=admin,
            )

            # Increment the user_count for the respective admin
            admin.user_count += 1
            admin.save()
            print(admin_id)
            messages.success(request, "Customer created successfully!")
            return redirect("onboard")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "onboard.html")
def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login")

