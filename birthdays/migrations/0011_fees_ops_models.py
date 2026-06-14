from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def backfill_payment_fees(apps, schema_editor):
    MpesaPayment = apps.get_model("birthdays", "MpesaPayment")
    UserGiftReceived = apps.get_model("birthdays", "UserGiftReceived")
    for payment in MpesaPayment.objects.all():
        gross = payment.amount or Decimal("0")
        fee = min((gross * Decimal("0.10")).quantize(Decimal("0.01")), Decimal("800"))
        net = gross - fee
        deposit_fee = Decimal("0")
        if gross > 200:
            deposit_fee = Decimal("200") if gross >= 40000 else (gross * Decimal("0.005")).quantize(Decimal("0.01"))
        MpesaPayment.objects.filter(pk=payment.pk).update(
            platform_fee=fee,
            net_amount=net,
            mpesa_deposit_fee=deposit_fee,
        )
        UserGiftReceived.objects.filter(payment_id=payment.pk).update(
            platform_fee=fee,
            net_amount=net,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("birthdays", "0010_cataloggift_description"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="mpesapayment",
            name="platform_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="net_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="mpesa_deposit_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="idempotency_key",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="usergiftreceived",
            name="net_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="usergiftreceived",
            name="platform_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="mpesa_withdrawal_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="mpesapayment",
            name="mpesa_receipt",
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("idempotency_key", models.CharField(db_index=True, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="birthdays.mpesapayment",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="HouseWithdrawal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("payout_phone", models.CharField(max_length=20)),
                ("mpesa_withdrawal_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=180)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="house_withdrawals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=30)),
                ("facebook_url", models.URLField(blank=True)),
                ("tiktok_url", models.URLField(blank=True)),
                ("instagram_url", models.URLField(blank=True)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="site/")),
                ("favicon", models.ImageField(blank=True, null=True, upload_to="site/")),
                ("platform_fee_percent", models.DecimalField(decimal_places=2, default=10, max_digits=5)),
                ("platform_fee_cap", models.DecimalField(decimal_places=2, default=800, max_digits=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name_plural": "Site settings"},
        ),
        migrations.RunPython(backfill_payment_fees, migrations.RunPython.noop),
    ]
