from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BirthdayPage,
    CatalogGift,
    GiftContribution,
    GiftOption,
    HouseWithdrawal,
    MpesaPayment,
    PaymentAttempt,
    SiteSettings,
    UserGiftReceived,
    UserProfile,
    WishlistItem,
    WithdrawalAuthorization,
    WithdrawalRequest,
)


def _image_preview(image, alt="Image"):
    if not image:
        return "—"
    try:
        url = image.url
    except (AttributeError, ValueError):
        return "—"
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener"><img src="{0}" alt="{1}" '
        'style="width:64px;height:64px;object-fit:cover;border-radius:8px;" /></a>',
        url,
        alt,
    )


class GiftOptionInline(admin.TabularInline):
    model = GiftOption
    extra = 0
    fields = ("label", "icon", "amount", "animation", "display_order")


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    fk_name = "profile"
    extra = 0
    fields = ("title", "target_amount", "description", "display_order")


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "account_reference",
        "profile",
        "gift_label",
        "amount",
        "platform_fee",
        "net_amount",
        "status",
        "payer_phone",
        "created_at",
    )
    list_filter = ("status", "created_at", "updated_at", "profile", "catalog_gift", "wishlist_item")
    search_fields = (
        "account_reference",
        "checkout_request_id",
        "mpesa_receipt",
        "payer_phone",
        "sender_name",
        "gift_label",
        "profile__username",
        "profile__user__email",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("profile", "catalog_gift", "wishlist_item")


@admin.register(CatalogGift)
class CatalogGiftAdmin(admin.ModelAdmin):
    list_display = ("name", "image_preview", "amount", "is_active", "display_order", "created_at")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    ordering = ("display_order", "id")
    readonly_fields = ("image_preview",)
    fields = ("name", "description", "amount", "image", "image_preview", "is_active", "display_order")

    @admin.display(description="Image")
    def image_preview(self, obj):
        return _image_preview(obj.image, obj.name)


@admin.register(BirthdayPage)
class BirthdayPageAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "slug", "age_turning", "birthday_date", "goal_amount", "created_at")
    list_filter = ("birthday_date", "created_at", "owner")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "owner__email")
    date_hierarchy = "created_at"
    inlines = [GiftOptionInline]
    raw_id_fields = ("owner",)


@admin.register(GiftOption)
class GiftOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "page", "amount", "display_order", "icon")
    list_filter = ("page", "amount")
    search_fields = ("label", "page__name", "page__slug")
    ordering = ("page", "display_order", "id")
    raw_id_fields = ("page",)


@admin.register(GiftContribution)
class GiftContributionAdmin(admin.ModelAdmin):
    list_display = ("page", "display_sender", "amount", "is_anonymous", "created_at")
    list_filter = ("is_anonymous", "created_at", "page", "option")
    search_fields = ("sender_name", "page__name", "page__slug", "message")
    date_hierarchy = "created_at"
    raw_id_fields = ("page", "option")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "page",
        "amount",
        "mpesa_withdrawal_fee",
        "status",
        "payout_phone",
        "mpesa_transaction_id",
        "created_at",
    )
    list_filter = ("status", "created_at", "processed_at", "page")
    search_fields = (
        "profile__username",
        "profile__user__email",
        "profile__gift_slug",
        "payout_phone",
        "note",
        "page__slug",
        "conversation_id",
        "originator_conversation_id",
    )
    readonly_fields = ("created_at", "processed_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("profile", "page")


@admin.register(WithdrawalAuthorization)
class WithdrawalAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("profile", "amount", "payout_phone", "expires_at", "verified_at", "created_at")
    list_filter = ("verified_at", "expires_at", "created_at", "withdrawal")
    search_fields = ("profile__user__email", "payout_phone")
    readonly_fields = ("created_at", "verified_at", "code_hash")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile_picture_preview", "username", "gift_slug", "display_name", "setup_completed", "birthday_date")
    search_fields = ("user__email", "username", "gift_slug", "wishlist_slug", "display_name")
    list_filter = ("setup_completed", "birthday_date", "user__is_active", "user__date_joined")
    raw_id_fields = ("user",)
    inlines = [WishlistItemInline]
    readonly_fields = ("profile_picture_preview",)

    @admin.display(description="Profile picture")
    def profile_picture_preview(self, obj):
        return _image_preview(obj.profile_picture, obj.display_name or obj.username or "Profile picture")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "target_amount", "display_order", "created_at")
    list_filter = ("created_at", "profile")
    search_fields = ("title", "profile__username", "profile__gift_slug", "description")
    ordering = ("display_order", "id")
    raw_id_fields = ("profile",)


@admin.register(UserGiftReceived)
class UserGiftReceivedAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "display_sender",
        "gift_label",
        "amount",
        "net_amount",
        "platform_fee",
        "is_anonymous",
        "created_at",
    )
    list_filter = ("is_anonymous", "created_at", "profile", "catalog_gift", "wishlist_item", "payment__status")
    search_fields = (
        "sender_name",
        "gift_label",
        "message",
        "profile__username",
        "profile__user__email",
        "payer_phone",
    )
    date_hierarchy = "created_at"
    raw_id_fields = ("profile", "catalog_gift", "wishlist_item", "payment")


@admin.register(HouseWithdrawal)
class HouseWithdrawalAdmin(admin.ModelAdmin):
    list_display = ("amount", "mpesa_withdrawal_fee", "payout_phone", "status", "created_by", "created_at")
    list_filter = ("status", "created_at", "created_by")
    search_fields = ("payout_phone", "note", "created_by__email")
    date_hierarchy = "created_at"
    raw_id_fields = ("created_by",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("contact_email", "contact_phone", "website_url", "logo_preview", "favicon_preview", "platform_fee_percent", "platform_fee_cap", "updated_at")
    search_fields = ("contact_email", "contact_phone")
    readonly_fields = ("logo_preview", "favicon_preview", "updated_at")
    fields = (
        "contact_email",
        "contact_phone",
        "website_url",
        "facebook_url",
        "tiktok_url",
        "instagram_url",
        "logo",
        "logo_preview",
        "favicon",
        "favicon_preview",
        "platform_fee_percent",
        "platform_fee_cap",
        "updated_at",
    )

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        return _image_preview(obj.logo, "Site logo")

    @admin.display(description="Favicon")
    def favicon_preview(self, obj):
        return _image_preview(obj.favicon, "Site favicon")


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "payment", "created_at")
    list_filter = ("created_at",)
    search_fields = ("idempotency_key", "payment__account_reference")
    date_hierarchy = "created_at"
    raw_id_fields = ("payment",)
