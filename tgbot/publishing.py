"""Запись объектов из бота в каталог сайта: создание, точечное обновление полей, удаление."""

from __future__ import annotations

import logging
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from listings.models import Listing, ListingImage
from listings.upload_validation import ALLOWED_IMAGE_EXTENSIONS, validate_gallery_image_file

from .fields import compose_address, format_usd
from .models import ListingChangeLog, TelegramEmployee
from .telegram_api import TelegramAPIError

logger = logging.getLogger('tgbot')

REQUIRED_DRAFT_FIELDS = {
    'cover': 'Обложка (фото фасада)',
    'title': 'Название объекта',
    'district': 'Микрорайон / район',
    'rooms': 'Количество комнат',
    'area': 'Площадь',
    'kind': 'Тип объекта',
    'price_usd': 'Стоимость',
    'realtor_name': 'Имя риэлтора',
    'realtor_phone': 'Телефон риэлтора',
    'description': 'Описание',
}


class PublishError(Exception):
    """Не удалось записать данные на сайт; текст показывается сотруднику."""


def listing_url(listing: Listing) -> str:
    base = settings.SITE_URL.rstrip('/')
    return base + reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})


def missing_draft_fields(draft: dict) -> list[str]:
    return [label for key, label in REQUIRED_DRAFT_FIELDS.items() if draft.get(key) in (None, '', [])]


def _download_image(client, photo: dict) -> ContentFile:
    try:
        data, file_path = client.download_file(photo['file_id'])
    except TelegramAPIError as e:
        logger.warning('tgbot download failed: %s', e)
        raise PublishError('Не удалось скачать фото из Telegram. Попробуйте отправить ещё раз.') from None
    ext = os.path.splitext(file_path)[1].lower() or '.jpg'
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise PublishError(f'Формат файла {ext} не поддерживается. Отправьте фото в JPG или PNG.')
    content = ContentFile(data, name=f'tg_{uuid.uuid4().hex[:16]}{ext}')
    try:
        validate_gallery_image_file(content)
    except ValidationError as e:
        raise PublishError(e.messages[0] if e.messages else 'Файл не является изображением.') from None
    return content


def _kind_to_category(kind: str) -> tuple[str, bool]:
    if kind == Listing.KIND_COMMERCIAL:
        return Listing.PROPERTY_COMMERCIAL, False
    if kind == Listing.KIND_LAND:
        return Listing.PROPERTY_RESIDENTIAL, True
    return Listing.PROPERTY_RESIDENTIAL, False


def _log(listing: Listing, employee: TelegramEmployee, action: str, field: str = '', old='', new=''):
    ListingChangeLog.objects.create(
        listing=listing,
        listing_public_uuid=listing.public_uuid,
        listing_title=listing.title,
        employee=employee,
        action=action,
        field=field,
        old_value=str(old),
        new_value=str(new),
    )


def _delete_files_on_commit(names: list[str]):
    def _cleanup():
        for name in names:
            try:
                default_storage.delete(name)
            except Exception:
                logger.warning('tgbot: не удалось удалить файл %s', name, exc_info=True)

    transaction.on_commit(_cleanup)


def publish_draft(client, employee: TelegramEmployee, draft: dict) -> Listing:
    missing = missing_draft_fields(draft)
    if missing:
        raise PublishError('Не заполнены поля: ' + ', '.join(missing))

    # Скачиваем всё до транзакции: при сбое сети на сайте не останется «половины» объекта.
    cover = _download_image(client, draft['cover'])
    gallery = [_download_image(client, p) for p in draft.get('photos') or []]

    category, is_land = _kind_to_category(draft['kind'])
    try:
        with transaction.atomic():
            listing = Listing(
                title=draft['title'],
                address=compose_address(draft['district'], draft.get('street') or ''),
                listing_type=Listing.TYPE_SALE,
                property_category=category,
                is_land_plot=is_land,
                object_kind=draft['kind'],
                price=format_usd(draft['price_usd']),
                price_usd=draft['price_usd'],
                rooms=draft['rooms'],
                area=draft['area'],
                description=draft['description'],
                realtor_name=draft['realtor_name'],
                realtor_phone=draft['realtor_phone'],
                is_published=True,
                telegram_author=employee,
                published_at=timezone.now(),
            )
            listing.image.save(cover.name, cover, save=False)
            listing.save()
            for order, content in enumerate(gallery, start=1):
                img = ListingImage(listing=listing, order=order)
                img.image.save(content.name, content, save=False)
                img.save()
            _log(listing, employee, ListingChangeLog.ACTION_CREATE, new=listing_url(listing))
    except Exception:
        logger.exception('tgbot: ошибка записи объекта в БД')
        raise PublishError('Не удалось сохранить объект на сайте.') from None
    return listing


def update_listing_field(client, employee: TelegramEmployee, listing: Listing, field: str, value) -> tuple[str, str]:
    """
    Меняет только выбранное поле существующей карточки (UUID и ссылка не меняются)
    и поднимает объект наверх каталога. Возвращает (было, стало) для сообщения.
    """
    now = timezone.now()
    old_image_name = None
    content = None

    if field == 'price':
        old, new = listing.price, format_usd(value)
        listing.price, listing.price_usd = new, value
        update_fields = ['price', 'price_usd']
    elif field == 'area':
        old, new = f'{listing.area} м²', f'{value} м²'
        listing.area = value
        update_fields = ['area']
    elif field == 'title':
        old, new = listing.title, value
        listing.title = value
        update_fields = ['title']
    elif field == 'description':
        old, new = listing.description, value
        listing.description = value
        update_fields = ['description']
    elif field == 'realtor':
        name, phone = value
        old = ', '.join(x for x in (listing.realtor_name, listing.realtor_phone) if x)
        new = f'{name}, {phone}'
        listing.realtor_name, listing.realtor_phone = name, phone
        update_fields = ['realtor_name', 'realtor_phone']
    elif field == 'cover':
        content = _download_image(client, value)
        old_image_name = listing.image.name if listing.image else None
        old, new = old_image_name or '—', content.name
        update_fields = ['image']
    else:
        raise PublishError('Это поле нельзя изменить.')

    try:
        with transaction.atomic():
            if content is not None:
                listing.image.save(content.name, content, save=False)
            listing.published_at = now
            listing.save(update_fields=update_fields + ['published_at', 'updated_at'])
            _log(listing, employee, ListingChangeLog.ACTION_UPDATE, field=field, old=old, new=new)
            if old_image_name:
                _delete_files_on_commit([old_image_name])
    except Exception:
        logger.exception('tgbot: ошибка обновления объекта %s', listing.pk)
        raise PublishError('Не удалось сохранить изменения на сайте.') from None
    return old, new


def delete_listing(employee: TelegramEmployee, listing: Listing) -> None:
    files = listing.media_file_names()
    try:
        with transaction.atomic():
            _log(listing, employee, ListingChangeLog.ACTION_DELETE, old=listing_url(listing))
            listing.delete()
            _delete_files_on_commit(files)
    except Exception:
        logger.exception('tgbot: ошибка удаления объекта %s', listing.pk)
        raise PublishError('Не удалось удалить объект с сайта.') from None
