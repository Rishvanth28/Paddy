from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import *

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

def create_admin(request):
    if request.method == "POST":
        phone_number = request.POST.get("phone_number")
        role = request.POST.get("role")
        # Validate the role and phone number
        if not phone_number or role != '0': # 0  is admin
            messages.error(request, "All fields are required.")
            return redirect("superadmin_dashboard")

        # check if the phone number already exists
        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already exists.")
            return redirect("superadmin_dashboard")
        
        # Check if the phone number is valid (e.g., length, format)
        if len(phone_number) < 10 or not phone_number.isdigit():
            messages.error(request, "Invalid phone number.")
            return redirect("superadmin_dashboard")
        
        # Check if the admin creating the user has sufficient user count
        current_user = request.session.get("user_id")
        current_admin = AdminTable.objects.get(admin_id=current_user)
        if current_admin.user_count <= 0:
            messages.error(request, "Insufficient user count.")
            return redirect("superadmin_dashboard")
        
        # Create a new admin
        try:
            new_admin = AdminTable.objects.create(
                phone_number=phone_number,
                password=phone_number,
                user_count=50,
            )
            new_admin.save()
            messages.success(request, "Admin created successfully!")
            return redirect("superadmin_dashboard")
        except Exception as e:
            messages.error(request, f"Error creating admin: {str(e)}")
            return redirect("superadmin_dashboard")

def create_customer(request):
    if request.method == "POST":
        phone_number = request.POST.get("phone_number")
        password = request.POST.get("password")

        if not phone_number or not password:
            messages.error(request, "All fields are required.")
            return redirect("create_customer")

        # Create a new customer
        try:
            new_customer = CustomerTable.objects.create(
                phone_number=phone_number,
                password=password,
            )
            new_customer.save()
            messages.success(request, "Customer created successfully!")
            return redirect("customer_dashboard")
        except Exception as e:
            messages.error(request, f"Error creating customer: {str(e)}")
            return redirect("create_customer")

def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login")

