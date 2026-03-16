from django.contrib import admin
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.http import Http404
from .models import Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    fields = ('image', 'image_url', 'order')


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'address', 'listing_type', 'price', 'rooms', 'area', 'is_published', 'gallery_count', 'bulk_upload_link', 'created_at')
    list_filter = ('is_published', 'listing_type')
    search_fields = ('title', 'address')
    ordering = ('-created_at',)
    inlines = [ListingImageInline]

    def gallery_count(self, obj):
        count = obj.listingimage_set.count()
        return f'{count} фото'
    gallery_count.short_description = 'Галерея'

    def bulk_upload_link(self, obj):
        url = reverse('admin:listing-bulk-upload', args=[obj.pk])
        return format_html('<a href="{}" class="button">📎 Загрузить фото</a>', url)
    bulk_upload_link.short_description = 'Загрузка'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/upload-gallery/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='listing-bulk-upload',
            ),
        ]
        return custom + urls

    def bulk_upload_view(self, request, pk):
        from django.template.response import TemplateResponse
        listing = get_object_or_404(Listing, pk=pk)

        if request.method == 'POST':
            files = request.FILES.getlist('images')
            if not files:
                messages.warning(request, 'Выберите хотя бы одно фото.')
            else:
                # Определяем порядок — после последнего существующего фото
                last_order = listing.listingimage_set.order_by('-order').values_list('order', flat=True).first() or 0
                created = 0
                for i, f in enumerate(files, start=1):
                    ListingImage.objects.create(listing=listing, image=f, order=last_order + i)
                    created += 1
                messages.success(request, f'Загружено {created} фото.')
                return redirect(reverse('admin:listings_listing_change', args=[pk]))

        context = {
            **self.admin_site.each_context(request),
            'listing': listing,
            'title': f'Загрузить фото: {listing.title}',
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/listings/bulk_upload.html', context)
