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

def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login")
