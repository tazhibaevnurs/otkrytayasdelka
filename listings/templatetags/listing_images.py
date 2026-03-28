"""Теги шаблонов для URL превью каталога."""
from django import template

from listings.catalog_images import listing_card_image_url as _listing_card_image_url

register = template.Library()


@register.simple_tag
def listing_card_image_url(listing):
    return _listing_card_image_url(listing)
