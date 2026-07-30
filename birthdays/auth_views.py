import logging
import traceback

from allauth.account.forms import ChangePasswordForm
from allauth.account.views import SignupView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import UserProfile
from .profile_utils import save_profile_from_request

logger = logging.getLogger(__name__)


class CustomSignupView(SignupView):
    template_name = "account/signup.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            logger.exception("Signup dispatch failed")
            if self._wants_json(request):
                return self._error_json(exc, status=500)
            raise

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as exc:
            logger.exception("Signup form_valid failed")
            if self._wants_json(self.request):
                return self._error_json(exc, status=500)
            raise

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["show_client_debug"] = settings.DEBUG
        return ctx

    @staticmethod
    def _wants_json(request):
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    @staticmethod
    def _error_json(exc, status=500):
        message = str(exc) if settings.DEBUG else "Server error while creating your account. Please try again shortly."
        payload = {
            "success": False,
            "errors": {"__all__": [message]},
            "status": status,
        }
        if settings.DEBUG:
            payload["debug"] = {
                "type": type(exc).__name__,
                "detail": str(exc),
                "traceback": traceback.format_exc()[:4000],
            }
        return JsonResponse(payload, status=status)


def _settings_context(profile, password_form=None, active_tab="profile", error=None):
    return {
        "profile": profile,
        "password_form": password_form or ChangePasswordForm(user=profile.user),
        "active_tab": active_tab,
        "error": error,
    }


@login_required
def profile_setup(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    active_tab = request.GET.get("tab", "profile")
    if active_tab not in ("profile", "password"):
        active_tab = "profile"

    if request.method == "POST":
        action = request.POST.get("action", "profile")

        if action == "password":
            password_form = ChangePasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Password updated.")
                return redirect(f"{reverse('profile-setup')}?tab=password")
            return render(
                request,
                "birthdays/profile_setup.html",
                _settings_context(profile, password_form, "password"),
            )

        error = save_profile_from_request(request.user, request, mark_complete=True)
        if error:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": {"profile": [error]}}, status=400)
            return render(
                request,
                "birthdays/profile_setup.html",
                _settings_context(profile, active_tab="profile", error=error),
            )

        redirect_url = reverse("dashboard")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "redirect": redirect_url})
        messages.success(request, "Profile updated.")
        return redirect(f"{reverse('profile-setup')}?tab=profile")

    return render(
        request,
        "birthdays/profile_setup.html",
        _settings_context(profile, active_tab=active_tab),
    )
