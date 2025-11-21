from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.utils.timezone import now
from datetime import timedelta
from paddy_app.models import AdminTable, CustomerTable, Subscription


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

        if not phone_number or not password:
            messages.error(request, "All fields are required.")
            return redirect("login_app:login")

        # Priority 1: Check if Superadmin (admin_id <= 1000000)
        try:
            admin_user = AdminTable.objects.get(phone_number=phone_number)
            if check_password(password, admin_user.password):
                # Check if superadmin
                if admin_user.admin_id <= 1000000:
                    request.session["user_id"] = admin_user.admin_id
                    request.session["role"] = "superadmin"
                    return redirect("superadmin_app:superadmin_dashboard")
                # Regular admin
                else:
                    request.session["user_id"] = admin_user.admin_id
                    request.session["role"] = "admin"
                    
                    # Check for any active product subscription (rice, paddy, pesticide)
                    active_product_sub = Subscription.objects.filter(
                        admin_id=admin_user, 
                        subscription_type__in=['admin_rice', 'admin_paddy', 'admin_pesticide'],
                        end_date__gte=now().date(),
                        subscription_status=1
                    ).first()
                    
                    if active_product_sub:
                        return redirect("admin_app:admin_dashboard")
                    else:
                        return redirect("payment_app:admin_product_subscription")
        except AdminTable.DoesNotExist:
            pass  # Continue to check customer

        # Priority 2: Check if Customer (only if not found in AdminTable or password didn't match)
        try:
            customer_user = CustomerTable.objects.get(phone_number=phone_number)
            if check_password(password, customer_user.password):
                request.session["user_id"] = customer_user.customer_id
                request.session["role"] = "customer"

                # Subscription check
                sub = Subscription.objects.filter(customer_id=customer_user, subscription_type="customer").order_by("-end_date").first()
                
                if sub:
                    if sub.end_date and sub.end_date >= now().date():
                        return redirect("customer_app:customer_dashboard")
                    else:
                        return redirect("payment_app:customer_subscription_payment")
                else:
                    # Free trial logic
                    Subscription.objects.create(
                        customer_id=customer_user,
                        subscription_type="customer",
                        subscription_status=1,
                        payment_amount=0,
                        start_date=now().date(),
                        end_date=now().date() + timedelta(days=30)
                    )
                    return redirect("customer_app:customer_dashboard")
        except CustomerTable.DoesNotExist:
            pass  # User not found in either table

        # If we reach here, credentials are invalid
        messages.error(request, "Invalid phone number or password.")

    return render(request, "login_app/login.html")   

def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login_app:login")

def admin_login_submit(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            admin = AdminTable.objects.get(email=email)
            if admin.check_password(password):
                request.session['user_id'] = admin.admin_id
                return redirect('superadmin_app:customers_under_admin')
        except AdminTable.DoesNotExist:
            pass
    return render(request, 'login_app/login.html', {'error': 'Invalid credentials'})