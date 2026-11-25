"""Цена объекта в сомах по курсу из админки (Каталог → Курс доллара)."""
from django import template

from listings.models import usd_to_kgs

register = template.Library()


@register.simple_tag
def price_kgs(listing):
    """«7 962 500 сом» или пустая строка, если нет цены в USD или курса."""
    amount = usd_to_kgs(listing.price_usd)
    if not amount:
        return ''
    return f'{amount:,}'.replace(',', ' ') + ' сом'
