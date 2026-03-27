from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from .catalog_params import catalog_params_to_querydict, parse_listing_catalog_get
from .models import Listing
from .pagination import ListingPageNumberPagination
from .serializers import ListingSerializer
from .throttles import AIDailyThrottle, BurstAnonRateThrottle, BurstUserRateThrottle

LISTINGS_PER_PAGE = 24

# Значение GET property_category для фильтра «Земельный участок» (не поле модели).
FILTER_CATEGORY_LAND = 'land'


def _pagination_pages(current, total, margin=2):
    """Номера страниц для вывода: 1, ..., current-1, current, current+1, ..., total."""
    if total <= 1:
        return []
    show = set()
    show.add(1)
    show.add(total)
    for i in range(max(1, current - margin), min(total, current + margin) + 1):
        show.add(i)
    result = []
    prev = 0
    for p in sorted(show):
        if prev and p - prev > 1:
            result.append(None)  # ellipsis
        result.append(p)
        prev = p
    return result


def listing_list(request):
    """Страница каталога: табы Продажа/Покупка, фильтры, пагинация 24 на странице."""
    p = parse_listing_catalog_get(request.GET)
    queryset = Listing.objects.filter(is_published=True).order_by('-created_at')

    if p.tab == 'sale':
        queryset = queryset.filter(listing_type=Listing.TYPE_SALE)
    elif p.tab == 'purchase':
        queryset = queryset.filter(listing_type=Listing.TYPE_PURCHASE)

    if p.rooms_int is not None:
        r = p.rooms_int
        if r >= 5:
            queryset = queryset.filter(rooms__gte=5)
        else:
            queryset = queryset.filter(rooms=r)
    if p.area_min_int is not None:
        queryset = queryset.filter(area__gte=p.area_min_int)
    if p.area_max_int is not None:
        queryset = queryset.filter(area__lte=p.area_max_int)
    if p.q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(title__icontains=p.q) | Q(address__icontains=p.q) | Q(description__icontains=p.q)
        )
    if p.property_category == FILTER_CATEGORY_LAND:
        queryset = queryset.filter(is_land_plot=True)
    elif p.property_category in {Listing.PROPERTY_COMMERCIAL, Listing.PROPERTY_RESIDENTIAL}:
        queryset = queryset.filter(property_category=p.property_category, is_land_plot=False)

    paginator = Paginator(queryset, LISTINGS_PER_PAGE)
    page_obj = paginator.get_page(p.page)
    pagination_pages = _pagination_pages(page_obj.number, page_obj.paginator.num_pages)

    # GET без page — канонические параметры после валидации (без «длинного» сырого q в URL)
    get_copy = catalog_params_to_querydict(p)
    base_query = get_copy.urlencode()
    get_no_type = get_copy.copy()
    get_no_type.pop('type', None)
    query_all = get_no_type.urlencode()
    get_sale = get_copy.copy()
    get_sale['type'] = 'sale'
    query_sale = get_sale.urlencode()
    get_purchase = get_copy.copy()
    get_purchase['type'] = 'purchase'
    query_purchase = get_purchase.urlencode()

    has_filters = bool(
        p.tab or p.rooms or p.area_min or p.area_max or p.q or p.property_category
    )
    context = {
        'listings': page_obj,
        'page_obj': page_obj,
        'pagination_pages': pagination_pages,
        'current_tab': p.tab,
        'filter_rooms': p.rooms,
        'filter_area_min': p.area_min,
        'filter_area_max': p.area_max,
        'filter_q': p.q,
        'filter_property_category': p.property_category,
        'base_query': base_query,
        'query_all': query_all,
        'query_sale': query_sale,
        'query_purchase': query_purchase,
        'has_filters': has_filters,
    }
    # AJAX: только сетка и пагинация без перезагрузки страницы
    if request.GET.get('partial') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'listings/list_partial.html', context)
    return render(request, 'listings/list.html', context)


def listing_detail_legacy_redirect(request, pk):
    """Старые ссылки /catalog/<int>/ → канонический URL с UUID."""
    listing = get_object_or_404(Listing, pk=pk, is_published=True)
    return HttpResponsePermanentRedirect(
        reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})
    )


def listing_detail(request, public_uuid):
    """Детальная страница объекта (публичный UUID в URL)."""
    listing = get_object_or_404(Listing, public_uuid=public_uuid, is_published=True)
    gallery_images = listing.get_gallery_images(request)
    if not gallery_images:
        gallery_images = ['https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200&q=80']
    return render(request, 'listings/detail.html', {'listing': listing, 'gallery_images': gallery_images})


@api_view(['POST'])
@throttle_classes([AIDailyThrottle, BurstUserRateThrottle, BurstAnonRateThrottle])
def ai_generate_stub(request):
    """Заглушка AI: лимиты free/pro по группе; замените на реальную генерацию."""
    pro = (
        request.user.is_authenticated
        and request.user.groups.filter(name=settings.AI_PRO_GROUP_NAME).exists()
    )
    return Response(
        {
            'detail': 'Эндпоинт-заглушка. Подключите модель и снимите заглушку.',
            'plan': 'pro' if pro else 'free',
        }
    )


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    """API: список объектов и деталь по public_uuid (список с пагинацией и лимитами)."""
    queryset = Listing.objects.filter(is_published=True)
    serializer_class = ListingSerializer
    pagination_class = ListingPageNumberPagination
    lookup_field = 'public_uuid'
