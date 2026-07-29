import os

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


def _env(name, default=""):
    """Read env var and strip accidental wrapping quotes from Railway/.env values."""
    value = os.environ.get(name, default)
    if value is None:
        return default
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


class Command(BaseCommand):
    help = "Create/update Django superuser and Site domain from environment variables."

    def handle(self, *args, **options):
        self._ensure_site()
        self._ensure_superuser()

    def _ensure_site(self):
        domain = _env("SITE_DOMAIN") or _env("RAILWAY_PUBLIC_DOMAIN") or "giftme.co.ke"
        name = _env("SITE_NAME") or "GiftMe"
        site_id = getattr(settings, "SITE_ID", 1)

        site, created = Site.objects.update_or_create(
            id=site_id,
            defaults={"domain": domain, "name": name},
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Site id={site.id} domain={site.domain}"))

    def _ensure_superuser(self):
        email = _env("DJANGO_SUPERUSER_EMAIL").lower()
        password = _env("DJANGO_SUPERUSER_PASSWORD")
        # Django admin authenticates on USERNAME_FIELD (= username).
        # Default username to email so /admin/ login with the email works.
        username = _env("DJANGO_SUPERUSER_USERNAME") or email

        if not email or not password:
            message = (
                "DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD must be set "
                "so Railway can create the admin user on deploy."
            )
            if getattr(settings, "IS_PRODUCTION", False):
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(f"Skipping superuser create: {message}"))
            return


        User = get_user_model()

        user = (
            User.objects.filter(email__iexact=email).first()
            or User.objects.filter(username__iexact=username).first()
            or User.objects.filter(username__iexact=email).first()
        )

        if user is None:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser username={username} email={email}"))
        else:
            # Keep username aligned with login identifier; free conflicting usernames.
            conflict = (
                User.objects.filter(username__iexact=username)
                .exclude(pk=user.pk)
                .first()
            )
            if conflict:
                conflict.username = f"{conflict.username}_old_{conflict.pk}"
                conflict.save(update_fields=["username"])

            user.username = username
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated superuser username={username} email={email}"))

        # Verify credentials immediately so a bad password never ships unnoticed.
        authed = authenticate(username=username, password=password)
        if authed is None and username != email:
            authed = authenticate(username=email, password=password)
        if authed is None:
            raise CommandError(
                "Superuser was saved but authenticate() failed. "
                "Check DJANGO_SUPERUSER_PASSWORD for Railway variable interpolation "
                "(avoid unescaped $ characters)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin ready. Sign in at /admin/ with username: {username}"
            )
        )
