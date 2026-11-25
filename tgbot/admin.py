from django.contrib import admin

from .models import BotSession, ListingChangeLog, TelegramEmployee


@admin.register(TelegramEmployee)
class TelegramEmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'telegram_id', 'username', 'is_active', 'can_manage_all', 'listings_count', 'created_at')
    list_filter = ('is_active', 'can_manage_all')
    search_fields = ('full_name', 'username', 'telegram_id')
    fieldsets = (
        (None, {
            'fields': ('full_name', 'telegram_id', 'username', 'is_active', 'can_manage_all'),
            'description': (
                'Telegram ID сотрудник увидит в ответе бота, если напишет ему без доступа. '
                'Снимите «Доступ разрешён», чтобы закрыть доступ, не удаляя историю.'
            ),
        }),
        ('Контакт риэлтора по умолчанию', {'fields': ('default_realtor_name', 'default_realtor_phone')}),
    )

    def listings_count(self, obj):
        return obj.listings.count()
    listings_count.short_description = 'Объектов'


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('employee', 'state', 'draft_title', 'updated_at')
    readonly_fields = ('employee', 'chat_id', 'state', 'draft', 'context', 'updated_at')

    def draft_title(self, obj):
        return (obj.draft or {}).get('title') or '—'
    draft_title.short_description = 'Черновик'

    def has_add_permission(self, request):
        return False


@admin.register(ListingChangeLog)
class ListingChangeLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'employee', 'action', 'listing_title', 'field', 'old_short', 'new_short')
    list_filter = ('action', 'field', 'employee')
    search_fields = ('listing_title', 'listing_public_uuid', 'employee__full_name')
    readonly_fields = [f.name for f in ListingChangeLog._meta.fields]
    date_hierarchy = 'created_at'

    def _short(self, value):
        return value if len(value) <= 60 else value[:60] + '…'

    def old_short(self, obj):
        return self._short(obj.old_value)
    old_short.short_description = 'Было'

    def new_short(self, obj):
        return self._short(obj.new_value)
    new_short.short_description = 'Стало'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
