from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.ops_login, name="ops-login"),
    path("login/submit/", views.ops_login_submit, name="ops-login-submit"),
    path("logout/", views.ops_logout, name="ops-logout"),
    path("", views.ops_overview, name="ops-overview"),
    path("deposits/", views.ops_deposits, name="ops-deposits"),
    path("gifts/", views.ops_gifts, name="ops-gifts"),
    path("gifts/save/", views.ops_gifts_save, name="ops-gifts-save"),
    path("gifts/delete/", views.ops_gifts_delete, name="ops-gifts-delete"),
    path("payouts/", views.ops_payouts, name="ops-payouts"),
    path("house-payouts/", views.ops_house_payouts, name="ops-house-payouts"),
    path("house-payout/", views.ops_house_payout, name="ops-house-payout"),
    path("settings/", views.ops_settings, name="ops-settings"),
    path("settings/save/", views.ops_settings_save, name="ops-settings-save"),
]
