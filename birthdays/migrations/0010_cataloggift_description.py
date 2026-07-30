from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("birthdays", "0009_mpesa_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="cataloggift",
            name="description",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
