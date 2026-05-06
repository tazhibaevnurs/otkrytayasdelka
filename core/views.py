from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.urls import reverse
from .forms import ContactForm
from .models import Employee, FeaturedMedia, SectionImage, Review, TeamPageSettings
from listings.models import Listing


def healthz(request):
    """Liveness/readiness probe endpoint for Docker/Nginx health checks."""
    return HttpResponse('ok', content_type='text/plain')


def _section_image_url(key, request=None, default=''):
    """URL изображения секции по ключу."""
    obj = SectionImage.objects.filter(key=key).first()
    if obj:
        return obj.get_url(request) or default
    return default


def home(request):
    featured_media = FeaturedMedia.objects.filter(is_active=True).first()
    # Фон hero по умолчанию — static/img/hero-home.png (можно переопределить в «Изображения секций», ключ home_hero)
    default_hero = request.build_absolute_uri(static('img/hero-home.png'))
    default_help = 'https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=800&q=80'
    context = {
        'featured_media': featured_media,
        'home_hero_url': _section_image_url('home_hero', request, default_hero),
        'advantage_1_url': _section_image_url('advantage_1', request, 'https://images.unsplash.com/photo-1560264280-88b68371db39?w=600&q=80'),
        'advantage_2_url': _section_image_url('advantage_2', request, 'https://images.unsplash.com/photo-1501139083538-0139583c060f?w=600&q=80'),
        'advantage_3_url': _section_image_url('advantage_3', request, 'https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=600&q=80'),
        'advantage_4_url': _section_image_url('advantage_4', request, 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=600&q=80'),
        'advantage_5_url': _section_image_url('advantage_5', request, 'https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=600&q=80'),
        'advantage_6_url': _section_image_url('advantage_6', request, 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=600&q=80'),
        'help_block_url': _section_image_url('help_block', request, default_help),
        'reviews': Review.objects.filter(is_active=True),
        'latest_listings': Listing.objects.filter(is_published=True)
        .defer('description')
        .order_by('-created_at')[:6],
    }
    return render(request, 'core/home.html', context)


def team(request):
    """Страница сотрудников."""
    employees = Employee.objects.filter(is_active=True)
    settings_obj = TeamPageSettings.objects.first()
    context = {
        'employees': employees,
        'team_badge': settings_obj.section_badge if settings_obj else '[ КОМАНДА ]',
        'team_title': settings_obj.section_title if settings_obj else 'Наши сотрудники',
        'team_description': settings_obj.section_description if settings_obj else (
            'Профессионалы, которые сопровождают сделки с недвижимостью: подбор объектов, '
            'переговоры, юридическая проверка и поддержка на каждом этапе.'
        ),
        'team_profile_label': settings_obj.profile_label if settings_obj else 'Профиль',
        'team_empty_bio_fallback': settings_obj.empty_bio_fallback if settings_obj else (
            'Специалист агентства «Открытая Сделка». Поможет с подбором объекта, '
            'переговорами и сопровождением сделки.'
        ),
    }
    return render(request, 'core/team.html', context)


def about(request):
    default_about = 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1200&q=80'
    context = {
        'about_image_url': _section_image_url('about_image', request, default_about),
        'about_image_fallback_url': default_about,
    }
    return render(request, 'core/about.html', context)


def services(request):
    return render(request, 'core/services.html')


def purchase(request):
    default_hero = 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1920&q=80'
    context = {'purchase_hero_url': _section_image_url('purchase_hero', request, default_hero)}
    return render(request, 'core/purchase.html', context)


def sale(request):
    default_hero = 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1920&q=80'
    context = {'sale_hero_url': _section_image_url('sale_hero', request, default_hero)}
    return render(request, 'core/sale.html', context)


def contacts(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # сохраняет в ContactRequest
            return redirect(reverse('contacts') + '?sent=1')
    else:
        form = ContactForm()
    sent = request.GET.get('sent') == '1'
    return render(request, 'core/contacts.html', {'form': form, 'sent': sent})


def privacy(request):
    """Страница «Политика в отношении обработки персональных данных»."""
    return render(request, 'core/privacy.html')


def csrf_failure(request, reason=''):
    """Пользовательская страница ошибки CSRF (без технических деталей для посетителя)."""
    return render(request, 'core/csrf_error.html', status=403)


def brand_logo(request):
    """Единый логотип сайта: основной файл — static/img/logo.png (остальные — запасные варианты)."""
    base = Path(settings.BASE_DIR) / 'static' / 'img'
    candidates = (
        ('logo.png', 'image/png'),
        ('logo.webp', 'image/webp'),
        ('logo.svg', 'image/svg+xml; charset=utf-8'),
    )
    for name, ctype in candidates:
        path = base / name
        if path.is_file():
            try:
                data = path.read_bytes()
            except OSError:
                continue
            resp = HttpResponse(data, content_type=ctype)
            resp['Cache-Control'] = 'public, max-age=86400'
            return resp
    raise Http404('Brand logo files missing') from None
