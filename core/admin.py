from django.contrib import admin
from django.utils.html import format_html
from .models import FeaturedMedia, SectionImage, Review, ContactRequest


@admin.register(SectionImage)
class SectionImageAdmin(admin.ModelAdmin):
    list_display = ('key', 'admin_preview', 'label', 'has_image')
    list_filter = ('key',)
    search_fields = ('key', 'label')

    def admin_preview(self, obj):
        url = obj.get_url()
        if not url:
            return '—'
        # Если задана ссылка — показываем текст (превью по URL может грузиться долго или давать 404)
        if obj.image_url and obj.image_url.strip():
            return format_html('<span style="color: #0a0;">Ссылка</span>')
        return format_html('<img src="{}" style="max-height: 40px; max-width: 80px; object-fit: cover;" />', url)
    admin_preview.short_description = 'Превью'

    def has_image(self, obj):
        return bool(obj.image or obj.image_url)
    has_image.boolean = True
    has_image.short_description = 'Есть фото'


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'phone', 'message')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {'fields': ('name', 'phone', 'message', 'status')}),
        ('Дата', {'fields': ('created_at',)}),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'text_short', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('author_name', 'text')

    def text_short(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text
    text_short.short_description = 'Текст'


@admin.register(FeaturedMedia)
class FeaturedMediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'is_active', 'order', 'updated_at')
    list_editable = ('is_active', 'order')
    list_filter = ('media_type', 'is_active')
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'is_active', 'order'),
        }),
        ('Медиа', {
            'fields': ('media_type', 'youtube_url', 'image', 'image_url'),
            'description': 'Укажите YouTube-ссылку для видео или загрузите/вставьте ссылку на картинку.',
        }),
        ('Кнопка', {
            'fields': ('link_label', 'link_url'),
        }),
    )
