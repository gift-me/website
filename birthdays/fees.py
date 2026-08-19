"""Platform and M-Pesa fee calculations."""

from decimal import Decimal, ROUND_HALF_UP

PLATFORM_FEE_RATE = Decimal("0.10")
PLATFORM_FEE_CAP = Decimal("800")

PAYOUT_FEE_TIERS = (
    (100, Decimal("0")),
    (500, Decimal("7")),
    (1000, Decimal("13")),
    (1500, Decimal("23")),
    (2500, Decimal("33")),
    (3500, Decimal("53")),
    (5000, Decimal("57")),
    (7500, Decimal("78")),
    (10000, Decimal("90")),
    (15000, Decimal("100")),
    (250000, Decimal("108")),
)


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_platform_fee(gross: Decimal, rate=None, cap=None) -> Decimal:
    rate = rate if rate is not None else PLATFORM_FEE_RATE
    cap = cap if cap is not None else PLATFORM_FEE_CAP
    fee = _quantize(gross * rate)
    return min(fee, cap)


def calculate_net_to_user(gross: Decimal, platform_fee: Decimal | None = None) -> Decimal:
    fee = platform_fee if platform_fee is not None else calculate_platform_fee(gross)
    return _quantize(gross - fee)


def calculate_mpesa_deposit_fee(gross: Decimal) -> Decimal:
    """Till receiving (Lipa na M-Pesa Buy Goods) — paid by the business."""
    if gross <= 200:
        return Decimal("0")
    if gross >= 40000:
        return Decimal("200")
    return _quantize(gross * Decimal("0.005"))


def calculate_mpesa_payout_fee(amount: Decimal) -> Decimal:
    """Till-to-customer send money — paid by the business."""
    value = int(amount)
    if value <= 0:
        return Decimal("0")
    for upper, fee in PAYOUT_FEE_TIERS:
        if value <= upper:
            return fee
    return PAYOUT_FEE_TIERS[-1][1]


# Backwards-compatible alias
calculate_mpesa_withdrawal_fee = calculate_mpesa_payout_fee
