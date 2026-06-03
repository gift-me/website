from decimal import Decimal, ROUND_DOWN


def whole_number(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_DOWN))
