from django.contrib import admin

from .models import (
    BirthdayPage,
    CatalogGift,
    GiftContribution,
    GiftOption,
    MpesaPayment,
    UserGiftReceived,
    UserProfile,
    WishlistItem,
    WithdrawalRequest,
)


class GiftOptionInline(admin.TabularInline):
    model = GiftOption
    extra = 0


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    fk_name = "profile"
    extra = 0


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = ("account_reference", "profile", "amount", "status", "payer_phone", "gift_label", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("account_reference", "checkout_request_id", "mpesa_receipt", "payer_phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CatalogGift)
class CatalogGiftAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "is_active", "display_order", "created_at")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(BirthdayPage)
class BirthdayPageAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "age_turning", "birthday_date", "goal_amount", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    inlines = [GiftOptionInline]


@admin.register(GiftContribution)
class GiftContributionAdmin(admin.ModelAdmin):
    list_display = ("page", "display_sender", "amount", "created_at")
    list_filter = ("is_anonymous", "created_at")
    search_fields = ("sender_name", "page__name", "message")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("profile", "amount", "status", "payout_phone", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("profile__gift_slug", "payout_phone", "note")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "username", "gift_slug", "display_name", "setup_completed")
    search_fields = ("user__email", "username", "gift_slug", "display_name")
    list_filter = ("setup_completed",)
    inlines = [WishlistItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "target_amount", "display_order", "created_at")
    search_fields = ("title", "profile__gift_slug")


@admin.register(UserGiftReceived)
class UserGiftReceivedAdmin(admin.ModelAdmin):
    list_display = ("profile", "display_sender", "gift_label", "amount", "created_at")
