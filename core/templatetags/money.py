from django import template

register = template.Library()


@register.filter
def usd(micros, places=4):
    """Format micro-credits (1 credit = $1) as dollars."""
    try:
        return f"{int(micros) / 1_000_000:.{int(places)}f}"
    except (TypeError, ValueError):
        return "0.00"


@register.filter
def price_per_mtok(micros):
    return f"{int(micros) / 1_000_000:.2f}"
