from django.contrib import admin

from .models import (
    BirthdayPage,
    CatalogGift,
    GiftContribution,
    GiftOption,
    MpesaPayment,
    PaymentAttempt,
    Payout,
    PayoutAuthorization,
    SiteSettings,
    UserGiftReceived,
    UserProfile,
    WishlistItem,
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
    list_filter = ("status", "created_at", "profile")
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
    list_display = ("name", "amount", "is_active", "display_order", "created_at")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    ordering = ("display_order", "id")
    fields = ("name", "description", "amount", "image", "is_active", "display_order")


@admin.register(BirthdayPage)
class BirthdayPageAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "slug", "age_turning", "birthday_date", "goal_amount", "created_at")
    list_filter = ("birthday_date", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "owner__email")
    date_hierarchy = "created_at"
    inlines = [GiftOptionInline]
    raw_id_fields = ("owner",)


@admin.register(GiftOption)
class GiftOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "page", "amount", "display_order", "icon")
    list_filter = ("page",)
    search_fields = ("label", "page__name", "page__slug")
    ordering = ("page", "display_order", "id")
    raw_id_fields = ("page",)


@admin.register(GiftContribution)
class GiftContributionAdmin(admin.ModelAdmin):
    list_display = ("page", "display_sender", "amount", "is_anonymous", "created_at")
    list_filter = ("is_anonymous", "created_at", "page")
    search_fields = ("sender_name", "page__name", "page__slug", "message")
    date_hierarchy = "created_at"
    raw_id_fields = ("page", "option")


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "profile",
        "page",
        "amount",
        "payout_fee",
        "status",
        "payout_phone",
        "mpesa_transaction_id",
        "created_at",
    )
    list_filter = ("kind", "status", "created_at")
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
    raw_id_fields = ("profile", "page", "created_by")


@admin.register(PayoutAuthorization)
class PayoutAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("profile", "amount", "payout_phone", "expires_at", "verified_at", "created_at")
    list_filter = ("verified_at", "created_at")
    search_fields = ("profile__user__email", "payout_phone")
    readonly_fields = ("created_at", "verified_at", "code_hash")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "username", "gift_slug", "display_name", "setup_completed", "birthday_date")
    search_fields = ("user__email", "username", "gift_slug", "wishlist_slug", "display_name")
    list_filter = ("setup_completed", "birthday_date")
    raw_id_fields = ("user",)
    inlines = [WishlistItemInline]


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
    list_filter = ("is_anonymous", "created_at", "profile")
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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("contact_email", "contact_phone", "website_url", "platform_fee_percent", "platform_fee_cap", "updated_at")
    search_fields = ("contact_email", "contact_phone")


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "payment", "created_at")
    list_filter = ("created_at",)
    search_fields = ("idempotency_key", "payment__account_reference")
    date_hierarchy = "created_at"
    raw_id_fields = ("payment",)
