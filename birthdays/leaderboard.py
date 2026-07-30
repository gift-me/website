"""Top gifters leaderboard for public gift/wishlist pages."""

from django.db.models import Count, Sum

from .models import MpesaPayment, UserGiftReceived


def get_top_gifters(profile, limit=10):
    base = UserGiftReceived.objects.filter(
        profile=profile,
        payment__status=MpesaPayment.Status.COMPLETED,
    )

    rows = []
    named = (
        base.filter(is_anonymous=False)
        .values("sender_name")
        .annotate(total=Sum("amount"), gifts=Count("id"))
        .order_by("-total")
    )
    for entry in named:
        name = (entry["sender_name"] or "").strip() or "Supporter"
        rows.append(
            {
                "name": name,
                "total": entry["total"] or 0,
                "gifts": entry["gifts"],
            }
        )

    anon = base.filter(is_anonymous=True).aggregate(total=Sum("amount"), gifts=Count("id"))
    if anon["total"]:
        rows.append(
            {
                "name": "Anonymous",
                "total": anon["total"],
                "gifts": anon["gifts"] or 0,
            }
        )

    rows.sort(key=lambda r: r["total"], reverse=True)
    for idx, row in enumerate(rows[:limit], start=1):
        row["rank"] = idx
    return rows[:limit]
