from datetime import timedelta
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.shortcuts import redirect
from .models import Subscription

class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        role = request.session.get("role")
        user_id = request.session.get("user_id")
        path = request.path

        # Allow access to these paths without subscription check
        exempt_paths = [
            "/login/", "/logout/",
            "/admin-subscription/", "/payment-success/",
            "/customer-subscription/", "/customer-payment-success/"
        ]

        if path in exempt_paths or path.startswith("/static/"):
            return None

        # Handle admin subscription
        if role == "admin":
            latest = Subscription.objects.filter(
                admin_id=user_id,
                subscription_type="admin",
                subscription_status=1
            ).order_by("-end_date").first()

            if not latest or not latest.end_date or latest.end_date < now().date():
                return redirect("admin_subscription_payment")

        # Handle customer subscription
        elif role == "customer":
            latest = Subscription.objects.filter(
                customer_id=user_id,
                subscription_type="customer",
                subscription_status=1
            ).order_by("-end_date").first()

            if not latest or not latest.end_date or latest.end_date < now().date():
                return redirect("customer_subscription_payment")

        return None
