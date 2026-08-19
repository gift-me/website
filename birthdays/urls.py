from django.urls import path

from . import mpesa_views, payout_views, views
from .auth_views import profile_setup

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact_redirect, name="contact"),
    path("privacy-policy/", views.privacy, name="privacy"),
    path("terms-of-service/", views.terms, name="terms"),
    path("accessibility/", views.accessibility, name="accessibility"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/setup/", profile_setup, name="profile-setup"),
    path("g/<slug:slug>/", views.user_gift_page, name="user-gift"),
    path("w/<slug:slug>/", views.user_wishlist_page, name="user-wishlist"),
    path("api/mpesa/stk-push/", mpesa_views.stk_push_initiate, name="mpesa-stk-push"),
    path("api/mpesa/callback/", mpesa_views.mpesa_callback, name="mpesa-callback"),
    path("api/mpesa/status/<int:payment_id>/", mpesa_views.payment_status, name="mpesa-payment-status"),
    path("api/payout/initiate/", payout_views.payout_initiate, name="payout-initiate"),
    path("api/payout/verify/", payout_views.payout_verify, name="payout-verify"),
    path("api/payout/status/<int:payout_id>/", payout_views.payout_status, name="payout-status"),
    path("api/mpesa/b2c/result/", payout_views.b2c_result_callback, name="mpesa-b2c-result"),
    path("api/mpesa/b2c/timeout/", payout_views.b2c_timeout_callback, name="mpesa-b2c-timeout"),
    path("create/", views.create_birthday_page, name="birthday-create"),
]
