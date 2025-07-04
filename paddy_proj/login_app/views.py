from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from .models import *
from django.db import IntegrityError
from datetime import date
from django.core.paginator import Paginator
from django.utils import timezone
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
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from paddy_app.models import Orders, OrderItems, Payments, AdminTable, CustomerTable
import os
from django.db.models import Q, Prefetch
from paddy_app.decorators import role_required
from paddy_app.helpers import *
from paddy_app.models import *


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))
# Create your views here.
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
                        return redirect("payment_app:admin_subscription_payment")
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
                            return redirect("payment_app:customer_subscription_payment")
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