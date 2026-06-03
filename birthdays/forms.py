from django import forms

from .models import BirthdayPage, GiftContribution, GiftOption


class BirthdayPageForm(forms.ModelForm):
    class Meta:
        model = BirthdayPage
        fields = [
            "name",
            "age_turning",
            "birthday_date",
            "bio",
            "cover_image_url",
            "goal_amount",
            "payout_phone",
            "payout_wallet_name",
        ]
        widgets = {
            "birthday_date": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 3, "placeholder": "Tell people what you are celebrating."}),
            "cover_image_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "goal_amount": forms.NumberInput(attrs={"min": "0", "step": "100"}),
            "payout_phone": forms.TextInput(attrs={"placeholder": "e.g. +2547..."}),
            "payout_wallet_name": forms.TextInput(attrs={"placeholder": "M-Pesa / Wallet name"}),
        }


class GiftContributionForm(forms.ModelForm):
    option = forms.ModelChoiceField(queryset=GiftOption.objects.none(), required=True)

    class Meta:
        model = GiftContribution
        fields = ["option", "sender_name", "message", "amount", "is_anonymous"]
        widgets = {
            "sender_name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "message": forms.TextInput(attrs={"placeholder": "Happy birthday!"}),
            "amount": forms.NumberInput(attrs={"min": "10", "step": "10"}),
        }

    def __init__(self, *args, **kwargs):
        page = kwargs.pop("page", None)
        super().__init__(*args, **kwargs)
        if page:
            self.fields["option"].queryset = page.gift_options.all()
            self.fields["option"].empty_label = None

    def clean(self):
        cleaned = super().clean()
        option = cleaned.get("option")
        amount = cleaned.get("amount")
        if option and option.amount is not None:
            cleaned["amount"] = option.amount
        elif option and option.amount is None and amount is None:
            self.add_error("amount", "Enter the amount for this gift.")
        return cleaned
