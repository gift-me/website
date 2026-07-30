from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def kes(value):
    """Format KES amounts; show decimals when under 1 or when cents matter."""
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError):
        return "0"
    if amount < Decimal("1"):
        return f"{amount:.2f}"
    if amount == amount.quantize(Decimal("1")):
        return f"{int(amount)}"
    return f"{amount:.2f}"
