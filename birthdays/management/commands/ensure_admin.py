from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Create/update Django superuser and Site domain from environment variables."

    def handle(self, *args, **options):
        self._ensure_site()
        self._ensure_superuser()

    def _ensure_site(self):
        domain = (
            os.environ.get("SITE_DOMAIN", "").strip()
            or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
            or "giftme.co.ke"
        )
        name = os.environ.get("SITE_NAME", "").strip() or "GiftMe"
        site_id = getattr(settings, "SITE_ID", 1)

        site, created = Site.objects.update_or_create(
            id=site_id,
            defaults={"domain": domain, "name": name},
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Site id={site.id} domain={site.domain}"))

    def _ensure_superuser(self):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip() or "admin"

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping superuser create: set DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD."
                )
            )
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.filter(username=username).first()

        if user is None:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser {email}"))
            return

        user.email = email
        user.username = username
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Updated superuser {email}"))
