"""Сжатие загруженных изображений для веба (Hero, секции)."""
from io import BytesIO

from django.core.files.base import ContentFile


def downscale_field_to_jpeg(image_field_file, max_size=(1920, 1080), quality=85) -> ContentFile:
    """Уменьшить до max_size (длинная сторона), сохранить как JPEG."""
    from PIL import Image

    image_field_file.open('rb')
    try:
        img = Image.open(image_field_file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        return ContentFile(buf.read())
    finally:
        image_field_file.close()
