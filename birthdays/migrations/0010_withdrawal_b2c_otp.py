from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("birthdays", "0009_mpesa_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="withdrawalrequest",
            name="conversation_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="originator_conversation_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="mpesa_transaction_id",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="result_desc",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="withdrawalrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("processing", "Processing"),
                    ("approved", "Approved"),
                    ("failed", "Failed"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="WithdrawalAuthorization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("payout_phone", models.CharField(max_length=20)),
                ("code_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="withdrawal_authorizations",
                        to="birthdays.userprofile",
                    ),
                ),
                (
                    "withdrawal",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="authorization",
                        to="birthdays.withdrawalrequest",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
