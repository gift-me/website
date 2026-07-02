from datetime import datetime, time
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def _new_uuid():
    return str(uuid.uuid4())


from .image_utils import compress_image_file


class CatalogGift(models.Model):
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="gifts/catalog/")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Gift"
        verbose_name_plural = "Gifts"

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, "file"):
            should_compress = True
            if self.pk:
                previous = CatalogGift.objects.filter(pk=self.pk).only("image").first()
                if previous and previous.image.name == self.image.name:
                    should_compress = False
            if should_compress:
                self.image = compress_image_file(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (KES {int(self.amount)})"


class BirthdayPage(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="birthday_pages", null=True, blank=True
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    age_turning = models.PositiveIntegerField()
    birthday_date = models.DateField()
    bio = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True)
    payout_phone = models.CharField(max_length=20, blank=True)
    payout_wallet_name = models.CharField(max_length=120, blank=True)
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "birthday"
            slug = base_slug
            count = 2
            while BirthdayPage.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("birthday-detail", kwargs={"slug": self.slug})

    @property
    def countdown_seconds(self):
        birthday_start = timezone.make_aware(
            datetime.combine(self.birthday_date, time.min),
            timezone.get_current_timezone(),
        )
        delta = birthday_start - timezone.now()
        return max(int(delta.total_seconds()), 0)

    @property
    def total_raised(self):
        value = self.gifts.aggregate(total=models.Sum("amount"))["total"] or 0
        return value

    @property
    def total_withdrawn(self):
        value = self.withdrawals.filter(status=WithdrawalRequest.Status.APPROVED).aggregate(
            total=models.Sum("amount")
        )["total"] or 0
        return value

    @property
    def available_balance(self):
        return self.total_raised - self.total_withdrawn

    @property
    def gifts_count(self):
        return self.gifts.count()

    @property
    def progress_percent(self):
        if self.goal_amount <= 0:
            return 0
        percent = (float(self.total_raised) / float(self.goal_amount)) * 100
        return min(int(percent), 100)

    def __str__(self):
        return f"{self.name} turns {self.age_turning}"


class GiftOption(models.Model):
    page = models.ForeignKey(BirthdayPage, on_delete=models.CASCADE, related_name="gift_options")
    label = models.CharField(max_length=60)
    icon = models.CharField(max_length=40, help_text="Font Awesome icon class, e.g. fa-cake-candles")
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    animation = models.CharField(max_length=40, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        unique_together = ("page", "label")

    def __str__(self):
        suffix = "Any Amount" if self.amount is None else f"KES {int(self.amount)}"
        return f"{self.label} ({suffix})"


class GiftContribution(models.Model):
    page = models.ForeignKey(BirthdayPage, on_delete=models.CASCADE, related_name="gifts")
    option = models.ForeignKey(
        GiftOption, on_delete=models.SET_NULL, related_name="contributions", null=True, blank=True
    )
    sender_name = models.CharField(max_length=120, blank=True)
    message = models.CharField(max_length=220, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def display_sender(self):
        if self.is_anonymous or not self.sender_name.strip():
            return "Anonymous"
        return self.sender_name

    def __str__(self):
        return f"{self.display_sender} -> {self.page.slug} ({self.amount})"


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    profile = models.ForeignKey(
        "UserProfile", on_delete=models.CASCADE, related_name="withdrawals", null=True, blank=True
    )
    page = models.ForeignKey(
        BirthdayPage, on_delete=models.CASCADE, related_name="withdrawals", null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_phone = models.CharField(max_length=20, blank=True)
    note = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    conversation_id = models.CharField(max_length=64, blank=True, db_index=True)
    originator_conversation_id = models.CharField(max_length=64, blank=True, db_index=True)
    mpesa_transaction_id = models.CharField(max_length=32, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Withdrawal {self.amount} ({self.status})"


class WithdrawalAuthorization(models.Model):
    profile = models.ForeignKey("UserProfile", on_delete=models.CASCADE, related_name="withdrawal_authorizations")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_phone = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    withdrawal = models.OneToOneField(
        WithdrawalRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorization",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Withdrawal OTP {self.profile_id} ({self.amount})"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    username = models.CharField(max_length=50, blank=True, unique=True, null=True)
    gift_slug = models.CharField(max_length=36, unique=True, blank=True, null=True)
    wishlist_slug = models.CharField(max_length=36, unique=True, blank=True, null=True)
    display_name = models.CharField(max_length=120, blank=True)
    birthday_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    payout_phone = models.CharField(max_length=20, blank=True)
    setup_completed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.gift_slug:
            self.gift_slug = _new_uuid()
        if not self.wishlist_slug:
            self.wishlist_slug = _new_uuid()
        super().save(*args, **kwargs)

    def get_gift_url_path(self):
        return reverse("user-gift", kwargs={"slug": self.gift_slug})

    def get_wishlist_url_path(self):
        return reverse("user-wishlist", kwargs={"slug": self.wishlist_slug})

    @property
    def total_raised(self):
        return self.gifts_received.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def total_withdrawn(self):
        return self.withdrawals.filter(status=WithdrawalRequest.Status.APPROVED).aggregate(
            total=models.Sum("amount")
        )["total"] or 0

    @property
    def reserved_withdrawal_total(self):
        return self.withdrawals.filter(
            status__in=[
                WithdrawalRequest.Status.PENDING,
                WithdrawalRequest.Status.PROCESSING,
                WithdrawalRequest.Status.APPROVED,
            ]
        ).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def pending_otp_total(self):
        return self.withdrawal_authorizations.filter(
            verified_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def available_balance(self):
        return self.total_raised - self.reserved_withdrawal_total - self.pending_otp_total

    @property
    def gifts_count(self):
        return self.gifts_received.count()

    def __str__(self):
        return self.username or self.display_name or self.user.email


class UserGiftReceived(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="gifts_received")
    catalog_gift = models.ForeignKey(
        "CatalogGift", on_delete=models.SET_NULL, related_name="contributions", null=True, blank=True
    )
    wishlist_item = models.ForeignKey(
        "WishlistItem", on_delete=models.SET_NULL, related_name="contributions", null=True, blank=True
    )
    payment = models.OneToOneField(
        "MpesaPayment", on_delete=models.SET_NULL, related_name="gift_record", null=True, blank=True
    )
    sender_name = models.CharField(max_length=120, blank=True)
    payer_phone = models.CharField(max_length=20, blank=True)
    gift_label = models.CharField(max_length=120, default="Gift")
    message = models.CharField(max_length=220, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def display_sender(self):
        if self.is_anonymous or not self.sender_name.strip():
            return "Anonymous"
        return self.sender_name


class WishlistItem(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="wishlist_items", null=True, blank=True)
    title = models.CharField(max_length=120)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=220, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]

    @property
    def raised_amount(self):
        total = self.contributions.aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def progress_percent(self):
        if self.target_amount <= 0:
            return 0
        return min(int((float(self.raised_amount) / float(self.target_amount)) * 100), 100)

    def __str__(self):
        return f"{self.title} ({self.profile.gift_slug if self.profile else '?'})"


class MpesaPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="mpesa_payments")
    catalog_gift = models.ForeignKey(
        CatalogGift, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    wishlist_item = models.ForeignKey(
        WishlistItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    sender_name = models.CharField(max_length=120, blank=True)
    payer_phone = models.CharField(max_length=20)
    message = models.CharField(max_length=220, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gift_label = models.CharField(max_length=120, default="Gift")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    account_reference = models.CharField(max_length=12, unique=True)
    checkout_request_id = models.CharField(max_length=64, blank=True, db_index=True)
    merchant_request_id = models.CharField(max_length=64, blank=True)
    mpesa_receipt = models.CharField(max_length=32, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.account_reference} ({self.status})"
