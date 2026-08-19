import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_merge_house_withdrawals(apps, schema_editor):
    HouseWithdrawal = apps.get_model("birthdays", "HouseWithdrawal")
    Payout = apps.get_model("birthdays", "Payout")
    for row in HouseWithdrawal.objects.all().iterator():
        payout = Payout.objects.create(
            kind="house",
            amount=row.amount,
            payout_phone=row.payout_phone,
            payout_fee=row.mpesa_withdrawal_fee,
            note=row.note,
            status=row.status,
            created_by_id=row.created_by_id,
        )
        Payout.objects.filter(pk=payout.pk).update(created_at=row.created_at)


def backwards_split_house_withdrawals(apps, schema_editor):
    HouseWithdrawal = apps.get_model("birthdays", "HouseWithdrawal")
    Payout = apps.get_model("birthdays", "Payout")
    for row in Payout.objects.filter(kind="house").iterator():
        HouseWithdrawal.objects.create(
            amount=row.amount,
            payout_phone=row.payout_phone,
            mpesa_withdrawal_fee=row.payout_fee,
            note=row.note,
            status=row.status if row.status in ("pending", "approved", "rejected") else "pending",
            created_by_id=row.created_by_id,
            created_at=row.created_at,
        )
        row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("birthdays", "0013_merge_20260702_1558"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(old_name="WithdrawalRequest", new_name="Payout"),
        migrations.RenameModel(old_name="WithdrawalAuthorization", new_name="PayoutAuthorization"),
        migrations.RenameField(
            model_name="payout",
            old_name="mpesa_withdrawal_fee",
            new_name="payout_fee",
        ),
        migrations.RenameField(
            model_name="payoutauthorization",
            old_name="withdrawal",
            new_name="payout",
        ),
        migrations.AddField(
            model_name="payout",
            name="kind",
            field=models.CharField(
                choices=[("user", "User withdrawal"), ("house", "House withdrawal")],
                db_index=True,
                default="user",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="payout",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payouts_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payouts",
                to="birthdays.userprofile",
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="page",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payouts",
                to="birthdays.birthdaypage",
            ),
        ),
        migrations.AlterField(
            model_name="payoutauthorization",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payout_authorizations",
                to="birthdays.userprofile",
            ),
        ),
        migrations.AlterField(
            model_name="payoutauthorization",
            name="payout",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="authorization",
                to="birthdays.payout",
            ),
        ),
        migrations.RunPython(forwards_merge_house_withdrawals, backwards_split_house_withdrawals),
        migrations.DeleteModel(name="HouseWithdrawal"),
    ]
