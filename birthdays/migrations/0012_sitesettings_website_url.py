from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("birthdays", "0011_fees_ops_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="website_url",
            field=models.CharField(
                blank=True,
                help_text="Public site URL shown on QR downloads (e.g. giftme.co). No https:// needed.",
                max_length=200,
            ),
        ),
    ]
