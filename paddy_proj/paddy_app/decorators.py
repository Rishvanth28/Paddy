from functools import wraps
from django.shortcuts import render
from django.http import HttpResponseForbidden

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_role = request.session.get("role")
            if user_role not in allowed_roles:
                return render(request, "unauthorized.html", status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
