"""
Вывод числового price_usd из строкового поля price (типичные подписи в каталоге).
Нужно для фильтра «Цена»: на продакшене historical-записи часто имеют только text price.
"""

from __future__ import annotations

INF_CAP = 55_000_000


def infer_price_usd_from_charfield(raw: str | None) -> int | None:
    """
    Извлекает примерную сумму USD из текста («74 500 $», «До 115 000», «85 500»).

    «По запросу», только текст без цифр → None.

    Логика: все цифры подряд (как парсинг GET price_min / price_max).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    lowered = s.lower()
    skip_markers = (
        'по запросу',
        'договорн',
        'negotiable',
        'цена при осмотре',
        'цену уточняйте',
    )
    if any(m in lowered for m in skip_markers):
        return None

    digits_only = ''.join(ch for ch in s if ch.isdigit())
    if not digits_only:
        return None

    try:
        n = int(digits_only)
    except ValueError:
        return None

    if n <= 0:
        return None
    if n > INF_CAP:
        return None
    return n
