"""Контекст-процессоры: данные для всех шаблонов."""

DEFAULT_CTA_BG = 'https://static.tildacdn.one/tild3935-6463-4838-b366-396530316164/71bc35ce-0dc6-45d3-8.JPG'


def section_images(request):
    """Добавляет в контекст URL фона блока «Призыв к действию» (CTA)."""
    if not request:
        return {'cta_background_url': DEFAULT_CTA_BG}
    try:
        from .models import SectionImage
        obj = SectionImage.objects.filter(key='cta_bg').first()
        url = obj.get_url(request) if obj else ''
        return {'cta_background_url': url or DEFAULT_CTA_BG}
    except Exception:
        return {'cta_background_url': DEFAULT_CTA_BG}
