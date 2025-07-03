from django.shortcuts import render, redirect
from django.contrib import messages
from paddy_app.models import AdminTable, CustomerTable, Subscription
from django.utils.timezone import now
from datetime import timedelta

def profile(request):
    """
    Unified profile view that handles superadmin, admin, and customer profiles
    using a single template but different context data based on role.
    """
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
    
    # Keep the base_template separate in the context
    context = {
        'user_data': user_data,
        'role': role,
        'base_template': base_template,  # Pass the base template
    }
    return render(request, 'profile_app/profile.html', context)
