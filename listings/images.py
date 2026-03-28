"""Обработка изображений объявлений (превью для каталога)."""
from __future__ import annotations

from core.image_utils import downscale_field_to_jpeg


def thumbnail_jpeg_from_image_field(image_field_file, max_size=(720, 540), quality=82):
    """JPEG-превью для карточки каталога (ограничение по длинной стороне, без апскейла)."""
    return downscale_field_to_jpeg(image_field_file, max_size=max_size, quality=quality)
