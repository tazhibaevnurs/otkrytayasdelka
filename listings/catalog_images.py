"""Единая логика URL картинки для карточек каталога (шаблоны, API)."""
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

CATALOG_PLACEHOLDER = (
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688'
    '?w=640&h=480&fit=crop&q=75&auto=format'
)


def squeeze_unsplash_url(url: str, max_w: int = 720) -> str:
    if not url or 'images.unsplash.com' not in url:
        return url
    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    try:
        w = int(qs.get('w', max_w))
    except (TypeError, ValueError):
        w = max_w
    qs['w'] = str(min(w, max_w))
    qs['q'] = '75'
    qs.setdefault('auto', 'format')
    return urlunparse(parsed._replace(query=urlencode(qs)))


def listing_card_image_url(listing) -> str:
    if getattr(listing, 'image_thumbnail', None):
        return listing.image_thumbnail.url
    if listing.image:
        return listing.image.url
    if listing.image_url:
        return squeeze_unsplash_url(listing.image_url)
    return CATALOG_PLACEHOLDER
