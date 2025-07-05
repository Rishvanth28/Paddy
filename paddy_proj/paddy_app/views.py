from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from .models import *
from django.db import IntegrityError
from datetime import date, timedelta
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.timezone import now
from .decorators import role_required
from .helpers import *
from .helpers import create_notification
import json
from django.db.models import Q, Case, When, Sum, Count, F, Prefetch
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from .models import Orders, OrderItems, Payments, AdminTable, CustomerTable, Subscription


def home(request):
    """
    Home page view - redirects users based on their session role
    """
    role = request.session.get('role')
    
    if role == 'superadmin':
        return redirect('superadmin_app:superadmin_dashboard')
    elif role == 'admin':
        return redirect('admin_app:admin_dashboard')
    elif role == 'customer':
        return redirect('customer_app:customer_dashboard')
    else:
        # If no valid session, redirect to login
        return redirect('login_app:login')


def profile(request):
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    if not role or not user_id:
        messages.error(request, "Please log in to view your profile.")
        return redirect('login_app:login')
    
    # Determine base template and fetch user data based on role
    if role == 'superadmin':
        base_template = 'superadmin_app/superadmin_base.html'
        try:
            user = AdminTable.objects.get(admin_id=user_id)
            user_data = {
                'user_type': 'Super Admin',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'admin_id': user.admin_id,
                'user_count': user.user_count,
                'created_at': user.created_at,
                'is_superadmin': True,
            }
        except AdminTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
            
    elif role == 'admin':
        base_template = 'admin_app/admin_base.html'
        try:
            user = AdminTable.objects.get(admin_id=user_id)
            # Get subscription info for admin
            subscription = Subscription.objects.filter(
                admin_id=user, 
                subscription_type="admin"
            ).order_by('-end_date').first()
            
            user_data = {
                'user_type': 'Admin',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'admin_id': user.admin_id,
                'user_count': user.user_count,
                'created_at': user.created_at,
                'subscription': subscription,
                'is_admin': True,
            }
        except AdminTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
            
    elif role == 'customer':
        base_template = 'customer_app/customer_base.html'
        try:
            user = CustomerTable.objects.get(customer_id=user_id)
            # Get subscription info for customer
            subscription = Subscription.objects.filter(
                customer_id=user, 
                subscription_type="customer"
            ).order_by('-end_date').first()
            
            user_data = {
                'user_type': 'Customer',
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'customer_id': user.customer_id,
                'company_name': user.company_name,
                'gst': user.GST,
                'address': user.address,
                'admin': user.admin,
                'created_at': user.created_at,
                'subscription': subscription,
                'is_customer': True,
            }
        except CustomerTable.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('login_app:login')
    else:
        messages.error(request, "Invalid role.")
        return redirect('login_app:login')
    
    context = {
        'base_template': base_template,
        'user_data': user_data,
        'role': role,
    }
    return render(request, 'profile.html', context)

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
            return redirect("customer_app:customer_dashboard")

        except CustomerTable.DoesNotExist:
            messages.warning(request, "You don't have a Customer account linked. Please subscribe or contact support.")
            return redirect("admin_app:admin_dashboard")

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
            return redirect("admin_app:admin_dashboard")

        except AdminTable.DoesNotExist:
            messages.warning(request, "You don't have an Admin account linked. Please subscribe or contact support.")
            return redirect("customer_app:customer_dashboard")

    messages.error(request, "Invalid session. Please log in again.")
    return redirect("login_app:login")

@role_required(["superadmin"])  
def get_admins_api(request):
    """API endpoint to get all admins for superadmin"""
    if request.method == 'GET':
        try:
            admins = AdminTable.objects.all().values('admin_id', 'first_name', 'last_name', 'email')
            return JsonResponse({
                'success': True,
                'admins': list(admins)
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@role_required(["superadmin", "admin"])
def update_order_delivery_status_api(request):
    """API endpoint to update order delivery status"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            order_id = data.get('order_id')
            delivery_status = data.get('delivery_status')
            
            if not order_id or delivery_status is None:
                return JsonResponse({
                    'error': 'Missing order_id or delivery_status'
                }, status=400)
            
            try:
                order = Orders.objects.get(order_id=order_id)
                order.delivery_status = delivery_status
                order.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Order delivery status updated successfully'
                })
            except Orders.DoesNotExist:
                return JsonResponse({
                    'error': 'Order not found'
                }, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
