"""Проверка загружаемых изображений галереи в админке."""

import os

from django.core.exceptions import ValidationError
from PIL import Image

MAX_GALLERY_IMAGE_BYTES = 5 * 1024 * 1024  # 5 МБ
MAX_GALLERY_FILES_PER_REQUEST = 30
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}


def validate_gallery_image_file(uploaded) -> None:
    """
    Размер, расширение и фактическое содержимое через Pillow (MIME по заголовку не доверяем).
    """
    if uploaded.size > MAX_GALLERY_IMAGE_BYTES:
        raise ValidationError(
            f'Файл слишком большой (максимум {MAX_GALLERY_IMAGE_BYTES // (1024 * 1024)} МБ).'
        )
    name = getattr(uploaded, 'name', '') or ''
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            'Допустимы только изображения: JPG, PNG, WebP, GIF.'
        )
    uploaded.seek(0)
    try:
        with Image.open(uploaded) as img:
            img.verify()
    except Exception:
        raise ValidationError('Файл не является корректным изображением.')
    uploaded.seek(0)
