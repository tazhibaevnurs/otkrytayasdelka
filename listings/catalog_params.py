"""
Разбор и ограничение query-параметров каталога (защита от DoS и слишком длинного поиска).

Django ORM дальше использует параметризованные запросы — без конкатенации SQL.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.http import QueryDict

# Верхние границы (подбираются под предметную область)
MAX_CATALOG_PAGE = 10_000
MAX_SEARCH_QUERY_LEN = 200
MAX_AREA_VALUE = 2_147_483_647  # разумный потолок для м²
MAX_ROOMS_DIGIT = 99  # одиночный фильтр «ровно N комнат»
MAX_PRICE_USD = 55_000_000  # потолок GET price_min/max (анти‑DoS)


@dataclass
class CatalogParams:
    page: int
    tab: str  # '', 'sale', 'purchase'
    rooms: str  # сырой для UI: '', '1'..'4', '5' для 5+
    rooms_int: int | None  # для фильтра queryset
    area_min: str
    area_max: str
    area_min_int: int | None
    area_max_int: int | None
    q: str
    property_category: str  # '', 'land', 'residential', 'commercial'
    land_plot_legacy: bool
    price_min: str  # сырое из GET для поля ввода
    price_max: str
    price_min_usd: int | None  # None — ограничение не задано
    price_max_usd: int | None


def _clamp_page(raw: str | None) -> int:
    if raw is None or raw == '':
        return 1
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return 1
    if n < 1:
        return 1
    return min(n, MAX_CATALOG_PAGE)


def _parse_tab(raw: str | None) -> str:
    v = (raw or '').strip().lower()
    if v in ('sale', 'purchase'):
        return v
    return ''


def _parse_rooms(raw: str | None) -> tuple[str, int | None]:
    s = (raw or '').strip()
    if not s.isdigit():
        return s, None
    n = min(max(int(s), 0), MAX_ROOMS_DIGIT)
    return str(n), n


def _digits_only_positive(raw: str | None, cap: int) -> tuple[str, int | None]:
    """Строки с пробелами/табуляцией; пустое — нет ограничения."""
    if raw is None:
        return '', None
    s = ''.join(c for c in str(raw).strip().replace('\u00a0', ' ') if c.isdigit())
    if not s:
        return '', None
    n = min(int(s), cap)
    if n < 0:
        return '', None
    return str(n), n


def _parse_area(raw: str | None) -> tuple[str, int | None]:
    s = (raw or '').strip()
    if not s.isdigit():
        return s, None
    n = int(s)
    if n < 0:
        return '0', None
    n = min(n, MAX_AREA_VALUE)
    return str(n), n


def _parse_q(raw: str | None) -> str:
    q = (raw or '').strip()
    if len(q) > MAX_SEARCH_QUERY_LEN:
        return q[:MAX_SEARCH_QUERY_LEN]
    return q


def _parse_property_category(raw: str | None, land_plot: str | None) -> tuple[str, bool]:
    from .models import Listing

    v = (raw or '').strip().lower()
    legacy = (land_plot or '').strip().lower() == '1'
    allowed = {'', 'land', Listing.PROPERTY_RESIDENTIAL, Listing.PROPERTY_COMMERCIAL}
    if v not in allowed:
        v = ''
    if not v and legacy:
        v = 'land'
    return v, legacy


def parse_listing_catalog_get(GET) -> CatalogParams:
    """GET — QueryDict или обычный dict-подобный объект."""
    page = _clamp_page(GET.get('page'))
    tab = _parse_tab(GET.get('type'))
    rooms_str, rooms_int = _parse_rooms(GET.get('rooms'))
    area_min_s, area_min_i = _parse_area(GET.get('area_min'))
    area_max_s, area_max_i = _parse_area(GET.get('area_max'))
    q = _parse_q(GET.get('q'))
    prop, land_legacy = _parse_property_category(GET.get('property_category'), GET.get('land_plot'))

    pm_s, pm_i = _digits_only_positive(GET.get('price_min'), MAX_PRICE_USD)
    px_s, px_i = _digits_only_positive(GET.get('price_max'), MAX_PRICE_USD)
    if pm_i is not None and px_i is not None and pm_i > px_i:
        pm_i, px_i = px_i, pm_i
        pm_s, px_s = str(pm_i), str(px_i)

    return CatalogParams(
        page=page,
        tab=tab,
        rooms=rooms_str,
        rooms_int=rooms_int,
        area_min=area_min_s,
        area_max=area_max_s,
        area_min_int=area_min_i,
        area_max_int=area_max_i,
        q=q,
        property_category=prop,
        land_plot_legacy=land_legacy,
        price_min=pm_s,
        price_max=px_s,
        price_min_usd=pm_i,
        price_max_usd=px_i,
    )


def catalog_params_to_querydict(p: CatalogParams) -> QueryDict:
    """Канонические GET-параметры фильтра (без page) для ссылок и пагинации."""
    qd = QueryDict(mutable=True)
    if p.tab:
        qd['type'] = p.tab
    if p.rooms:
        qd['rooms'] = p.rooms
    if p.area_min:
        qd['area_min'] = p.area_min
    if p.area_max:
        qd['area_max'] = p.area_max
    if p.q:
        qd['q'] = p.q
    if p.property_category:
        qd['property_category'] = p.property_category
    elif p.land_plot_legacy:
        qd['land_plot'] = '1'
    if p.price_min:
        qd['price_min'] = p.price_min
    if p.price_max:
        qd['price_max'] = p.price_max
    return qd
