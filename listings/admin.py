from django.contrib import admin
from .models import Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    fields = ('image', 'image_url', 'order')


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'address', 'listing_type', 'price', 'rooms', 'area', 'is_published', 'created_at')
    list_filter = ('is_published', 'listing_type')
    search_fields = ('title', 'address')
    ordering = ('-created_at',)
    inlines = [ListingImageInline]
