"""Пагинация API: верхняя граница номера страницы и размера страницы."""

from rest_framework.pagination import PageNumberPagination


class ListingPageNumberPagination(PageNumberPagination):
    page_size = 24
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 100
    max_page_number = 10_000

    def get_page_number(self, request, paginator):
        page_number = request.query_params.get(self.page_query_param) or 1
        if page_number in self.last_page_strings:
            return paginator.num_pages or 1
        try:
            n = int(page_number)
        except (TypeError, ValueError):
            n = 1
        n = max(1, min(n, self.max_page_number))
        if paginator.num_pages:
            n = min(n, paginator.num_pages)
        return n
