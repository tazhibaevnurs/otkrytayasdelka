from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import ContactForm
from .models import FeaturedMedia, SectionImage, Review


def _section_image_url(key, request=None, default=''):
    """URL изображения секции по ключу."""
    obj = SectionImage.objects.filter(key=key).first()
    if obj:
        return obj.get_url(request) or default
    return default


def home(request):
    featured_media = FeaturedMedia.objects.filter(is_active=True).first()
    default_hero = 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1920&q=80'
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
    }
    return render(request, 'core/home.html', context)


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
    """Страница «Политика конфиденциальности» (заглушка до наполнения)."""
    return render(request, 'core/privacy.html')
