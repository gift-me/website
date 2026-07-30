"""Ops dashboard analytics and ledger helpers."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from birthdays.models import HouseWithdrawal, MpesaPayment, UserProfile, WithdrawalRequest

User = get_user_model()


def _completed_payments():
    return MpesaPayment.objects.filter(status=MpesaPayment.Status.COMPLETED)


def total_deposits_gross():
    return _completed_payments().aggregate(total=Sum("amount"))["total"] or Decimal("0")


def total_house_profit():
    return _completed_payments().aggregate(total=Sum("platform_fee"))["total"] or Decimal("0")


def total_mpesa_deposit_fees():
    return _completed_payments().aggregate(total=Sum("mpesa_deposit_fee"))["total"] or Decimal("0")


def total_user_withdrawals():
    approved = WithdrawalRequest.objects.filter(status=WithdrawalRequest.Status.APPROVED)
    gross = approved.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    fees = approved.aggregate(total=Sum("mpesa_withdrawal_fee"))["total"] or Decimal("0")
    return gross, fees


def total_house_withdrawals():
    approved = HouseWithdrawal.objects.filter(status=HouseWithdrawal.Status.APPROVED)
    gross = approved.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    fees = approved.aggregate(total=Sum("mpesa_withdrawal_fee"))["total"] or Decimal("0")
    return gross, fees


def available_house_profit():
    approved_house = HouseWithdrawal.objects.filter(status=HouseWithdrawal.Status.APPROVED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    pending_house = HouseWithdrawal.objects.filter(status=HouseWithdrawal.Status.PENDING).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    return total_house_profit() - approved_house - pending_house


def estimated_mpesa_balance():
    deposits = total_deposits_gross()
    deposit_fees = total_mpesa_deposit_fees()
    user_gross, user_fees = total_user_withdrawals()
    house_gross, house_fees = total_house_withdrawals()
    return deposits - deposit_fees - user_gross - user_fees - house_gross - house_fees


def overview_stats():
    user_gross, user_fees = total_user_withdrawals()
    house_gross, house_fees = total_house_withdrawals()
    return {
        "total_users": User.objects.count(),
        "total_deposits": total_deposits_gross(),
        "total_payments": _completed_payments().count(),
        "house_profit": total_house_profit(),
        "available_house_profit": available_house_profit(),
        "user_withdrawals_gross": user_gross,
        "user_withdrawal_fees": user_fees,
        "house_withdrawals_gross": house_gross,
        "house_withdrawal_fees": house_fees,
        "mpesa_deposit_fees": total_mpesa_deposit_fees(),
        "estimated_mpesa_balance": estimated_mpesa_balance(),
    }


def revenue_chart(days=30):
    since = timezone.now() - timedelta(days=days)
    rows = (
        _completed_payments()
        .filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("amount"), count=Count("id"), house=Sum("platform_fee"))
        .order_by("day")
    )
    return [
        {
            "day": row["day"].isoformat() if row["day"] else "",
            "total": float(row["total"] or 0),
            "count": row["count"],
            "house": float(row["house"] or 0),
        }
        for row in rows
    ]


def payment_status_chart():
    labels = {
        MpesaPayment.Status.PENDING: "Pending",
        MpesaPayment.Status.COMPLETED: "Completed",
        MpesaPayment.Status.FAILED: "Failed",
        MpesaPayment.Status.CANCELLED: "Cancelled",
    }
    rows = MpesaPayment.objects.values("status").annotate(count=Count("id"))
    return [
        {"label": labels.get(row["status"], row["status"]), "value": row["count"], "status": row["status"]}
        for row in rows
    ]


def revenue_breakdown_chart():
    completed = _completed_payments()
    net = completed.aggregate(total=Sum("net_amount"))["total"] or Decimal("0")
    house = completed.aggregate(total=Sum("platform_fee"))["total"] or Decimal("0")
    mpesa = completed.aggregate(total=Sum("mpesa_deposit_fee"))["total"] or Decimal("0")
    return [
        {"label": "To creators", "value": float(net)},
        {"label": "House profit", "value": float(house)},
        {"label": "M-Pesa deposit fees", "value": float(mpesa)},
    ]


def gifts_last_7_days():
    since = timezone.now() - timedelta(days=7)
    rows = (
        _completed_payments()
        .filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    return [{"day": row["day"].isoformat() if row["day"] else "", "count": row["count"]} for row in rows]


def filter_payments(q="", status=""):
    qs = MpesaPayment.objects.select_related("profile", "profile__user").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            models.Q(mpesa_receipt__icontains=q)
            | models.Q(account_reference__icontains=q)
            | models.Q(payer_phone__icontains=q)
            | models.Q(checkout_request_id__icontains=q)
            | models.Q(profile__username__icontains=q)
        )
    return qs


def filter_user_withdrawals(q="", status=""):
    qs = WithdrawalRequest.objects.select_related("profile", "profile__user").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            models.Q(payout_phone__icontains=q)
            | models.Q(profile__username__icontains=q)
            | models.Q(note__icontains=q)
        )
    return qs


def filter_house_withdrawals(q="", status=""):
    qs = HouseWithdrawal.objects.select_related("created_by").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(models.Q(payout_phone__icontains=q) | models.Q(note__icontains=q))
    return qs
