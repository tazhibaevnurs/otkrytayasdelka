from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from .models import Listing
from .serializers import ListingSerializer

LISTINGS_PER_PAGE = 24


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
    queryset = Listing.objects.filter(is_published=True).order_by('-created_at')

    # Таб: тип объявления
    tab = (request.GET.get('type') or '').strip().lower()
    if tab == 'sale':
        queryset = queryset.filter(listing_type=Listing.TYPE_SALE)
    elif tab == 'purchase':
        queryset = queryset.filter(listing_type=Listing.TYPE_PURCHASE)

    # Фильтры
    rooms = request.GET.get('rooms', '').strip()
    if rooms.isdigit():
        r = int(rooms)
        if r >= 5:
            queryset = queryset.filter(rooms__gte=5)
        else:
            queryset = queryset.filter(rooms=r)
    area_min = request.GET.get('area_min', '').strip()
    if area_min.isdigit():
        queryset = queryset.filter(area__gte=int(area_min))
    area_max = request.GET.get('area_max', '').strip()
    if area_max.isdigit():
        queryset = queryset.filter(area__lte=int(area_max))
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(address__icontains=q) | Q(description__icontains=q)
        )

    paginator = Paginator(queryset, LISTINGS_PER_PAGE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    pagination_pages = _pagination_pages(page_obj.number, page_obj.paginator.num_pages)

    # GET без page — для пагинации и табов
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
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

    has_filters = bool(tab or rooms or area_min or area_max or q)
    context = {
        'listings': page_obj,
        'page_obj': page_obj,
        'pagination_pages': pagination_pages,
        'current_tab': tab,
        'filter_rooms': rooms,
        'filter_area_min': area_min,
        'filter_area_max': area_max,
        'filter_q': q,
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


def listing_detail(request, pk):
    """Детальная страница объекта."""
    listing = get_object_or_404(Listing, pk=pk, is_published=True)
    gallery_images = listing.get_gallery_images(request)
    if not gallery_images:
        gallery_images = ['https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200&q=80']
    return render(request, 'listings/detail.html', {'listing': listing, 'gallery_images': gallery_images})


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    """API: список объектов и деталь по id."""
    queryset = Listing.objects.filter(is_published=True)
    serializer_class = ListingSerializer
