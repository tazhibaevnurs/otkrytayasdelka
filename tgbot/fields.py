"""Разбор и форматирование значений, которые сотрудник вводит в бота."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from listings.models import Listing
from listings.price_infer import INF_CAP

MAX_TITLE_LEN = 255
MAX_ADDRESS_LEN = 255
MAX_REALTOR_NAME_LEN = 120
MAX_DESCRIPTION_LEN = 20_000
MAX_PHOTOS = 30
MAX_ROOMS = 50
MAX_AREA = 1_000_000

KIND_CHOICES = dict(Listing.KIND_CHOICES)


class FieldError(ValueError):
    """Ошибка ввода: текст сообщения показывается сотруднику."""


def group_thousands(n: int) -> str:
    return f'{n:,}'.replace(',', ' ')


def format_usd(n: int) -> str:
    return f'{group_thousands(n)} $'


def format_kgs(n: int) -> str:
    return f'{group_thousands(n)} сом'


def parse_price_usd(text: str) -> int:
    raw = (text or '').strip().lower()
    multiplier = 1
    # «91к», «91 тыс» — частая запись у риэлторов
    if re.search(r'\d\s*(к|k|тыс\.?|т)\s*\$?$', raw):
        multiplier = 1000
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise FieldError('Введите стоимость числом, например: 91 000')
    value = int(digits) * multiplier
    if value <= 0 or value > INF_CAP:
        raise FieldError('Стоимость выглядит некорректно. Введите сумму в долларах, например: 91 000')
    return value


def parse_area(text: str) -> int:
    raw = (text or '').lower().replace('м²', '').replace('м2', '').replace('кв.м', '').replace('кв', '')
    raw = raw.replace(',', '.').strip()
    match = re.search(r'\d+(?:\.\d+)?', raw.replace(' ', ''))
    if not match:
        raise FieldError('Введите площадь числом в м², например: 67')
    try:
        value = Decimal(match.group(0))
    except InvalidOperation:
        raise FieldError('Введите площадь числом в м², например: 67') from None
    area = int(value.quantize(Decimal('1')))
    if area <= 0 or area > MAX_AREA:
        raise FieldError('Площадь выглядит некорректно. Введите число в м², например: 67')
    return area


def parse_rooms(text: str) -> int:
    raw = (text or '').strip()
    if not raw.isdigit():
        raise FieldError('Введите количество комнат числом, например: 2')
    rooms = int(raw)
    if rooms > MAX_ROOMS:
        raise FieldError(f'Количество комнат не может быть больше {MAX_ROOMS}.')
    return rooms


def normalize_phone(text: str) -> str:
    raw = (text or '').strip()
    if not re.fullmatch(r'[\d\s+()\-]+', raw):
        raise FieldError('Номер телефона может содержать только цифры, пробелы, «+», «-» и скобки.')
    digits = re.sub(r'\D', '', raw)
    if not 9 <= len(digits) <= 15:
        raise FieldError('Введите номер телефона полностью, например: 0509 349 199')
    return re.sub(r'\s+', ' ', raw)[:25]


def clean_line(text: str, max_len: int, label: str) -> str:
    value = re.sub(r'\s+', ' ', (text or '')).strip()
    if not value:
        raise FieldError(f'{label} не может быть пустым.')
    if len(value) > max_len:
        raise FieldError(f'{label} слишком длинное (максимум {max_len} символов).')
    return value


def clean_description(text: str) -> str:
    # Абзацы и переносы строк сохраняем как есть, убираем только пробелы по краям.
    value = (text or '').replace('\r\n', '\n').strip()
    if not value:
        raise FieldError('Описание не может быть пустым.')
    if len(value) > MAX_DESCRIPTION_LEN:
        raise FieldError(f'Описание слишком длинное (максимум {MAX_DESCRIPTION_LEN} символов).')
    return value


def parse_photo_order(text: str, count: int) -> list[int]:
    """
    «3 1 2» → индексы [2, 0, 1]. Можно указать только часть номеров:
    они встанут первыми, остальные сохранят исходный порядок.
    """
    numbers = re.findall(r'\d+', text or '')
    if not numbers:
        raise FieldError('Введите номера фото через пробел, например: 3 1 2')
    order = []
    for n in numbers:
        idx = int(n) - 1
        if idx < 0 or idx >= count:
            raise FieldError(f'Фото с номером {n} нет. Доступны номера от 1 до {count}.')
        if idx in order:
            raise FieldError(f'Номер {n} указан дважды.')
        order.append(idx)
    order += [i for i in range(count) if i not in order]
    return order


def compose_address(district: str, street: str) -> str:
    return f'{district}, {street}' if street else district


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Режет длинный текст по абзацам/строкам под лимит сообщения Telegram."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ''
    for line in text.split('\n'):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ''
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f'{current}\n{line}' if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
