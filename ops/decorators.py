from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="ops-login")
        if not request.user.is_staff:
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper
