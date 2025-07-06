from datetime import timedelta
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.shortcuts import redirect
from .models import Subscription
from .helpers import get_unread_notification_count

class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        role = request.session.get("role")
        user_id = request.session.get("user_id")
        path = request.path

        # Allow access to these paths without subscription check
        exempt_paths = [
            "/login/", "/login/logout/",
            "/payment/admin-subscription-payment/", "/payment/admin-payment-success/",
            "/payment/customer-subscription-payment/", "/payment/customer-payment-success/",
        ]

        # Check if path starts with /admin/ (Django admin) or is in exempt paths
        if path.startswith("/admin/") or path in exempt_paths or path.startswith("/static/"):
            return None

        # If user is not logged in (no role or user_id), redirect to login
        # But allow access to Django admin
        if not role or not user_id:
            if not path.startswith("/admin/"):
                return redirect("login_app:login")

        # Handle admin subscription
        if role == "admin":
            latest = Subscription.objects.filter(
                admin_id=user_id,
                subscription_type="admin",
                subscription_status=1
            ).order_by("-end_date").first()

            if not latest or not latest.end_date or latest.end_date < now().date():
                return redirect("payment_app:admin_subscription_payment")

        # Handle customer subscription
        elif role == "customer":
            latest = Subscription.objects.filter(
                customer_id=user_id,
                subscription_type="customer",
                subscription_status=1
            ).order_by("-end_date").first()

            if not latest or not latest.end_date or latest.end_date < now().date():
                return redirect("payment_app:customer_subscription_payment")

        return None

class NotificationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        role = request.session.get("role")
        user_id = request.session.get("user_id")
        
        # Set default value
        request.unread_count = 0
        
        # Only calculate unread notifications if user is logged in
        if user_id and role:
            if role == "customer":
                request.unread_count = get_unread_notification_count('customer', user_id)
            elif role == "admin":
                request.unread_count = get_unread_notification_count('admin', user_id)
            elif role == "super_admin":
                request.unread_count = get_unread_notification_count('super_admin', user_id)
        
        return None
    
    def process_template_response(self, request, response):
        if hasattr(response, 'context_data'):
            response.context_data['unread_count'] = getattr(request, 'unread_count', 0)
        return response
