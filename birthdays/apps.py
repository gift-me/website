from django.apps import AppConfig


class BirthdaysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "birthdays"

    def ready(self):
        import birthdays.signals  # noqa: F401
