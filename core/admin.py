from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, FeaturedMedia, SectionImage, Review, ContactRequest


@admin.register(SectionImage)
class SectionImageAdmin(admin.ModelAdmin):
    readonly_fields = ('image_optimized',)
    list_display = ('key', 'admin_preview', 'label', 'has_image')
    list_filter = ('key',)
    search_fields = ('key', 'label')

    def admin_preview(self, obj):
        url = obj.get_url()
        if not url:
            return '—'
        # Внешняя ссылка — показываем превью; /media/ — «Файл», чтобы не было битой иконки при 404
        if url.startswith('http://') or url.startswith('https://'):
            return format_html('<img src="{}" style="max-height: 40px; max-width: 80px; object-fit: cover;" alt="" />', url)
        if obj.image:
            return format_html('<span style="color: #069;">Файл</span>')
        return format_html('<span style="color: #0a0;">Ссылка</span>')
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


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'admin_photo', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('full_name', 'position', 'bio')
    fieldsets = (
        (None, {'fields': ('full_name', 'position', 'bio', 'order', 'is_active')}),
        ('Фото', {'fields': ('photo', 'photo_url')}),
    )

    def admin_photo(self, obj):
        url = obj.photo_display_url
        if not url:
            return '—'
        if url.startswith('http://') or url.startswith('https://'):
            return format_html('<img src="{}" style="height: 40px; width: 40px; object-fit: cover; border-radius: 8px;" alt="" />', url)
        return format_html('<span style="color: #069;">Файл</span>')
    admin_photo.short_description = 'Фото'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'text_short', 'has_media', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('author_name', 'text')
    fieldsets = (
        (None, {'fields': ('author_name', 'text')}),
        ('Медиа', {'fields': ('image', 'image_url', 'video', 'video_url')}),
        ('Публикация', {'fields': ('order', 'is_active')}),
    )

    def text_short(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text
    text_short.short_description = 'Текст'

    def has_media(self, obj):
        return bool(obj.image or obj.image_url or obj.video or obj.video_url)
    has_media.boolean = True
    has_media.short_description = 'Есть медиа'


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
